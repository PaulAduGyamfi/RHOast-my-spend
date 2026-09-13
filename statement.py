import csv, io, json
from datetime import datetime

DATE_KEYS = ("transaction date", "posted date", "post date", "date")
DESC_KEYS = ("description", "merchant name", "merchant", "payee", "name", "details", "particulars", "narrative")
AMOUNT_KEYS = ("amount", "debit", "withdrawal", "value", "credit")
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m/%d/%y", "%d/%m/%y",
                "%d-%m-%Y", "%Y/%m/%d", "%b %d, %Y", "%d %b %Y", "%m-%d-%Y")


class StatementError(ValueError):
    pass


def to_iso(value):
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise StatementError(f"unrecognised date: {value!r}")


def to_amount(value):
    text = str(value).strip().replace(",", "").replace("$", "").replace("£", "").replace("€", "")
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    try:
        return abs(round(float(text), 2))
    except ValueError:
        raise StatementError(f"unrecognised amount: {value!r}")


def row(date, name, amount, descriptor=None, kind=None):
    return {"date": to_iso(date), "name": str(name).strip(), "transaction_type": kind,
            "original_description": descriptor or None, "amount": to_amount(amount)}


def from_json(text):
    data = json.loads(text)
    if isinstance(data, dict):
        for key in ("transactions", "added", "rows", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list) or not data:
        raise StatementError("JSON is not a non-empty list of transactions")
    out = []
    for r in data:
        if not isinstance(r, dict):
            raise StatementError("JSON list does not contain objects")
        name = r.get("merchant_name") or r.get("name") or r.get("description")
        if name is None:
            raise StatementError("JSON rows have no merchant name field")
        out.append(row(r.get("date") or r.get("transaction_date"), name, r.get("amount"),
                       r.get("original_description"), r.get("transaction_code") or r.get("transaction_type")))
    return out


def find_column(headers, keys):
    lowered = [h.strip().lower() for h in headers]
    for key in keys:
        if key in lowered:
            return lowered.index(key)
    for key in keys:
        for i, h in enumerate(lowered):
            if key in h:
                return i
    return None


def from_csv(text):
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = [r for r in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise StatementError("not enough CSV rows")
    date_i, desc_i, amt_i = (find_column(rows[0], k) for k in (DATE_KEYS, DESC_KEYS, AMOUNT_KEYS))
    if None in (date_i, desc_i, amt_i):
        raise StatementError("CSV header has no date, description and amount columns")
    out = []
    for r in rows[1:]:
        if max(date_i, desc_i, amt_i) >= len(r) or not r[amt_i].strip() or not r[date_i].strip():
            continue
        out.append(row(r[date_i], r[desc_i], r[amt_i], r[desc_i]))
    if not out:
        raise StatementError("CSV had headers but no readable rows")
    return out


def from_prose(text):
    from pydantic import BaseModel
    from llm import ai

    class Txn(BaseModel):
        date: str
        amount: float
        name: str
        original_description: str | None

    class Statement(BaseModel):
        transactions: list[Txn]

    prompt = ("Extract every transaction from this bank statement text.\n"
              "date must be YYYY-MM-DD. amount is the magnitude spent, always positive.\n"
              "name is the merchant descriptor exactly as printed.\n"
              "original_description is the full raw line, or null.\n"
              "Skip balances, totals, headers and interest summaries.\n\n" + text[:20000])
    msg = ai.messages.parse(model="claude-sonnet-5", max_tokens=8000,
                            messages=[{"role": "user", "content": prompt}], output_format=Statement)
    out = []
    for t in msg.parsed_output.transactions:
        if not t.name or not t.name.strip() or not t.amount:
            continue
        try:
            out.append(row(t.date, t.name, t.amount, t.original_description))
        except StatementError:
            continue
    if not out:
        raise StatementError("no transactions found in the pasted text")
    return out


def sniff(text):
    if text.lstrip().startswith(("[", "{")):
        return "json"
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 2 and any(d in lines[0] for d in (",", "\t", ";", "|")):
        return "csv"
    return "prose"


def parse(text, allow_model=True):
    if not text or not text.strip():
        raise StatementError("nothing pasted")
    order = {"json": (from_json, from_csv), "csv": (from_csv, from_json), "prose": ()}[sniff(text)]
    for reader in order:
        try:
            return reader(text), reader.__name__[5:]
        except (StatementError, json.JSONDecodeError, csv.Error):
            continue
    if not allow_model:
        raise StatementError("could not read this as JSON or CSV")
    return from_prose(text), "prose"
