import json

def normalize(r):
    return {
        "date":r["date"],
        "name":r["name"].strip(),
        "transaction_type": r["transaction_type"],
        "original_description": r["original_description"],
        "amount": round(float(r["amount"]), 2),
    }

def from_plaid(api_response):
    return [normalise({
    "date": t["date"],
    "name": t["merchant_name"],
    "transaction_type": t["transaction_code"],
    "original_description": t.get("original_description"),
    "amount": abs(float(t["amount"])),
}) for t in api_response["added"]]

def from_sampleJson(path="sample.json"):
    with open(path) as f:
        rows = json.load(f)
    return [normalise(r) for r in rows]