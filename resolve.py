import re
import json
from collections import Counter
from known_merchants import KNOWN, REFUSE_PREFIXES, BANK_INTERNAL, RESELLER_PREFIXES, SENSITIVE_CATS

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
 
    return "research", descriptor # Tavily
 
 
def is_sensitive(entry):
    return bool(entry) and isinstance(entry, dict) and entry["cat"] in SENSITIVE_CATS


if __name__ == "__main__":
     with open("sample.json") as f:
        STATUS = ["known", "research", "refuse", "internal"]
        rows = json.load(f)

        tally = Counter(resolve(r["name"])[0] for r in rows)

        for status, n in tally.most_common():
            print(f"{status:10} {n}")
 