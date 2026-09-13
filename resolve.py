import re
import json
from collections import Counter
from research import research
from ingest import load_transactions
from categories import SENSITIVE_CATS
from known_merchants import KNOWN, REFUSE_PREFIXES, BANK_INTERNAL, RESELLER_PREFIXES

_KEYS = list(KNOWN)

PREFIXES = r"^(SQ \*|TST\*|DD \*|SP |PY \*|POS DEBIT |PURCHASE |ACH |WIRE OUT |CKCD )"
NOISE    = r"(#\d+|\d{3}-\d{7}|\b\d{4,}\b|\.COM|\.CO|LLC|INC|\bNY\b|\bNYC\b)"

def clean(merchant_name):
    s = merchant_name.upper()
    s = re.sub(PREFIXES, "", s)
    s = re.sub(NOISE, " ", s)
    s = re.sub(r"[^A-Z& ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.title()


def resolve(descriptor):
    """Classify a descriptor. Returns (status, payload).
 
    ("known",    entry)  -> dictionary hit, free, no API call
    ("internal", entry)  -> bank fee or ATM, no merchant exists
    ("research", query)  -> send `query` to Tavily
    ("refuse",   None)   -> unidentifiable; say so rather than guessing
    """
    d = descriptor.upper()
 
    if d.startswith(REFUSE_PREFIXES):
        return "refuse", None
 
    for key, entry in BANK_INTERNAL.items():
        if key in d:
            return "internal", entry
 
    for prefix in RESELLER_PREFIXES:
        if d.startswith(prefix):
            remainder = descriptor[len(prefix):].strip()
            return ("research", remainder) if remainder else ("refuse", None)
 
    for key in _KEYS:
        if key.upper() in d:
            return "known", KNOWN[key]
 
    return "research", clean(descriptor)


UNIDENTIFIED = {"name": None, "cat": "unknown", "note": ""}


def unique_descriptors(txns):
    seen, order = set(), []
    for t in txns:
        if t["name"] not in seen:
            seen.add(t["name"])
            order.append(t["name"])
    return order


def identify(descriptor):
    status, payload = resolve(descriptor)

    if status == "research":
        try:
            return research(payload), "research"
        except Exception as exc:
            print(f"  research failed for {payload!r}: {type(exc).__name__}: {exc}")
            return dict(UNIDENTIFIED), "failed"
    if status == "refuse":
        return dict(UNIDENTIFIED), "refuse"
    return payload, status


def enrich_stream(txns):
    descriptors = unique_descriptors(txns)
    total = len(descriptors)
    resolved = {}

    for i, descriptor in enumerate(descriptors, 1):
        info, source = identify(descriptor)
        resolved[descriptor] = info
        hidden = is_sensitive(info)

        yield {
            "type": "merchant",
            "i": i,
            "total": total,
            "source": "filtered" if hidden else source,
            "descriptor": None if hidden else descriptor,
            "name": None if hidden else (info.get("name") or descriptor),
            "cat": None if hidden else info.get("cat"),
            "note": "" if hidden else (info.get("note") or ""),
            "txn_count": sum(1 for t in txns if t["name"] == descriptor),
        }

    out = []
    for t in txns:
        info = resolved[t["name"]]
        if is_sensitive(info):
            continue
        row = {**t, **info}
        if not row.get("name"):
            row["name"] = t["name"]
        out.append(row)

    yield {"type": "done", "enriched": out,
           "kept": len(out), "dropped": len(txns) - len(out)}


def enrich(txns):
    for event in enrich_stream(txns):
        if event["type"] == "done":
            return event["enriched"]
    return []
 
 
def is_sensitive(entry):
    return bool(entry) and isinstance(entry, dict) and entry["cat"] in SENSITIVE_CATS


if __name__ == "__main__":
    txns = load_transactions()
    enriched = enrich(txns)
    with open("enriched.json", "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"wrote {len(enriched)} enriched transactions")
 