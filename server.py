import json, os, traceback
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv()

import statement
from ingest import load_transactions
from resolve import enrich_stream, unique_descriptors
from detect import run_all
from profiler import write_profile
from roast import write_roast
from voice import speak

STATEMENT_PATH = "statement.json"
ENRICHED_PATH = "enriched.json"
AUDIO_PATH = "roast.mp3"
NO_STATEMENT = "no statement loaded, POST /statement first"
NO_ENRICHED = "no enriched data yet, run /enrich/stream first"

app = FastAPI(title="Roast My Spend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=500,
                        content={"detail": f"{type(exc).__name__}: {exc}", "where": request.url.path})


class StatementIn(BaseModel):
    text: str
    allow_model: bool = True


class RoastIn(BaseModel):
    profile: str | None = None


class SpeakIn(BaseModel):
    text: str


def load_json(path, missing):
    if not os.path.exists(path):
        raise HTTPException(409, missing)
    with open(path) as f:
        return json.load(f)


def save_json(path, rows):
    with open(path, "w") as f:
        json.dump(rows, f, indent=2)


def summary(rows, how):
    dates = sorted(r["date"] for r in rows)
    return {"count": len(rows), "format": how, "merchants": len(unique_descriptors(rows)),
            "window": [dates[0], dates[-1]], "total": round(sum(r["amount"] for r in rows), 2)}


@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html") as f:
        return f.read()


@app.get("/sample")
def sample():
    with open("sample.json") as f:
        return {"text": f.read()}


@app.post("/statement")
def load_statement(body: StatementIn):
    try:
        rows, how = statement.parse(body.text, allow_model=body.allow_model)
    except statement.StatementError as e:
        raise HTTPException(422, str(e))
    save_json(STATEMENT_PATH, rows)
    return summary(rows, how)


@app.post("/plaid")
def pull_from_plaid():
    rows = load_transactions(live=True)
    if not rows:
        raise HTTPException(422, "Plaid returned no spending transactions")
    save_json(STATEMENT_PATH, rows)
    return summary(rows, "plaid " + os.environ.get("PLAID_ENV", "sandbox"))


@app.get("/enrich/stream")
def stream():
    txns = load_json(STATEMENT_PATH, NO_STATEMENT)

    def events():
        try:
            for event in enrich_stream(txns):
                if event["type"] == "done":
                    save_json(ENRICHED_PATH, event.pop("enriched"))
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/findings")
def findings():
    rows = run_all(load_json(ENRICHED_PATH, NO_ENRICHED))
    return {"count": len(rows), "findings": rows}


@app.post("/profile")
def profile():
    rows = load_json(ENRICHED_PATH, NO_ENRICHED)
    return {"profile": write_profile(rows, run_all(rows))}


@app.post("/roast")
def roast(body: RoastIn | None = None):
    rows = load_json(ENRICHED_PATH, NO_ENRICHED)
    found = run_all(rows)
    if not found:
        raise HTTPException(422, "no findings, nothing worth roasting")
    text = body.profile if body and body.profile else write_profile(rows, found)
    return {"profile": text, "roast": write_roast(found, text)}


@app.post("/speak")
def speak_roast(body: SpeakIn):
    return FileResponse(speak(body.text, out=AUDIO_PATH), media_type="audio/mpeg", filename="roast.mp3")
