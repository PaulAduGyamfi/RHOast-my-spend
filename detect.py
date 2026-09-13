SENSITIVE_CATS = {"medical", "pharmacy", "legal", "childcare", "lender",
                  "religious", "charity", "adult", "recovery"}
 
 
def drop_sensitive(txns):
    """Hard filter. These never reach the model."""
    kept = []
    for t in txns:
        if t["cat"] in SENSITIVE_CATS:
            continue
        kept.append(t)
    return kept

def group_by_merchant(transactions):
    groups = {}
    for t in transactions:
        name = t["name"]
        if name not in groups:
            groups[name] = []
        groups[name].append(t)
    return groups

def days_between(date_a, date_b):
    from datetime import date
    a = date(*[int(x) for x in date_a.split("-")])
    b = date(*[int(x) for x in date_b.split("-")])
    return (b - a).days

def looks_monthly(rows):
    dates = sorted(r["date"] for r in rows)
    for i in range(len(dates) - 1):
        gap = days_between(dates[i], dates[i + 1])
        if gap < 20 or gap > 40:
            return False
    return True


def find_aspirational(groups):
    """One timme expensive charge."""
    found = []
    for name, rows in groups.items():
        if len(rows) != 1:
            continue
 
        only_txn = rows[0]
        if only_txn["amount"] < 150:
            continue
 
        found.append({
            "type": "aspirational",
            "merchant": name,
            "amount": only_txn["amount"],
            "date": only_txn["date"],
        })
    return found

def find_subscriptions(groups):
    """Monthly recurring charges"""
    found = []
    for name, rows in groups.items():
        if len(rows) < 3:
            continue

        amounts = [r["amount"] for r in rows]
        if len(set(amounts)) != 1:
            continue

        if not looks_monthly(rows):
            continue

        found.append({
            "type": "subscription",
            "merchant": name,
            "amount": amounts[0],
            "times": len(rows),
            "total": round(sum(amounts), 2),
        })
    return found

def find_zombies_charges(subscriptions, threshold=15.00):
    """Small recurring charges — the ones too cheap to notice on a statement."""
    found = []
    for sub in subscriptions:
        if sub["amount"] > threshold:
            continue
        found.append({
            "type": "zombie",
            "merchant": sub["merchant"],
            "amount": sub["amount"],
            "times": sub["times"],
            "annual_cost": round(sub["amount"] * 12, 2),
        })
    return found

def find_double_charges(groups):
    """Same merchant, same day, more than once."""
    found = []
    for name, rows in groups.items():
        by_date = {}
        for r in rows:
            by_date.setdefault(r["date"], []).append(r)
 
        for day, same_day in by_date.items():
            if len(same_day) < 2:
                continue
            found.append({
                "type": "double_charge",
                "merchant": name,
                "date": day,
                "count": len(same_day),
                "total": round(sum(r["amount"] for r in same_day), 2),
            })
    return found

def find_fees(txns):
    """Money that bought nothing."""
    fees = []
    for t in txns:
        if t["cat"] in ("bank fee", "late fee"):
            fees.append(t)
 
    if not fees:
        return []
 
    return [{
        "type": "fees",
        "total": round(sum(t["amount"] for t in fees), 2),
        "count": len(fees),
        "items": [{"date": t["date"], "name": t["name"], "amount": t["amount"]} for t in fees],
    }]


def headline_amount(finding):
    """The number a finding is judged on. Findings carry different keys."""
    for key in ("annual_cost", "total", "amount"):
        if key in finding:
            return finding[key]
    return 0.0


def run_all(txns):
    """Every detector, one list. Biggest number first.

    Takes enriched transactions (each needs date, name, amount, cat).
    Returns a flat list of finding dicts, each tagged with "type".
    """
    txns = drop_sensitive(txns)
    groups = group_by_merchant(txns)

    subscriptions = find_subscriptions(groups)
    zombies = find_zombies_charges(subscriptions)

    zombie_merchants = {z["merchant"] for z in zombies}
    big_subs = [s for s in subscriptions if s["merchant"] not in zombie_merchants]

    findings = [
        *zombies,
        *big_subs,
        *find_aspirational(groups),
        *find_double_charges(groups),
        *find_fees(txns),
    ]

    return sorted(findings, key=headline_amount, reverse=True)


if __name__ == "__main__":
    import json

    with open("enriched.json") as fh:
        txns = json.load(fh)

    findings = run_all(txns)
    print(f"{len(findings)} findings from {len(txns)} transactions\n")
    for item in findings:
        print(f"{item['type']:15} {headline_amount(item):>10,.2f}  {item.get('merchant', '')}")
