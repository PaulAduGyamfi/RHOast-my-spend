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
    return [normalize({
    "date": t["date"],
    "name": t["merchant_name"],
    "transaction_type": t["transaction_code"],
    "original_description": t.get("original_description"),
    "amount": abs(float(t["amount"])),
}) for t in api_response["added"]]

def from_sampleJson(path="sample.json"):
    with open(path) as f:
        rows = json.load(f)
    return [from_plaid({"added": rows})][0]

def load_transactions(live=False, path="sample.json"):
    """The only function the rest of the pipeline calls."""
    if live:
        from plaid_client import fetch_transactions   # write this when you wire Plaid
        return from_plaid(fetch_transactions())
    return from_sampleJson(path)

if __name__ == "__main__":
    txns = load_transactions()
    print(f"{len(txns)} transactions")
    print(f"{txns[0]['date']} .. {txns[-1]['date']}")
    print(f"net ${sum(t['amount'] for t in txns):,.2f}")
    print()
    for t in txns[:3]:
        print(t)