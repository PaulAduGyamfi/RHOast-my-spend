import json
import os
from collections import Counter
from datetime import date

from anthropic import Anthropic
from dotenv import load_dotenv
from detect import drop_sensitive

load_dotenv()
ai = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

PROFILE_SYSTEM = """From spending patterns alone, infer who this person is.
Cover: rough age band, city, whether they live alone, work pattern,
one habit they'd be surprised you spotted.

Tag every claim: [observed] straight from the data,
[inferred] derived with reasoning, [guess] plausible only.
Never infer health, relationships, or anything intimate — skip silently.
Under 100 words. Flat, factual tone. No jokes here."""


def weekday(iso_date):
    y, m, d = (int(x) for x in iso_date.split("-"))
    return date(y, m, d).weekday()


def profile_facts(txns):
    txns = drop_sensitive(txns)
    total = sum(t["amount"] for t in txns)

    by_cat = Counter()
    for t in txns:
        by_cat[t["cat"]] += t["amount"]

    by_merchant = Counter(t["name"] for t in txns)

    weekend = sum(t["amount"] for t in txns if weekday(t["date"]) >= 5)
    weekday_spend = total - weekend

    lunch_hours = sum(1 for t in txns if t["cat"] in ("restaurant", "coffee"))

    dates = sorted(t["date"] for t in txns)

    return {
        "window": [dates[0], dates[-1]],
        "transaction_count": len(txns),
        "total_spend": round(total, 2),
        "median_transaction": round(sorted(t["amount"] for t in txns)[len(txns) // 2], 2),
        "largest_transaction": round(max(t["amount"] for t in txns), 2),
        "spend_by_category": {k: round(v, 2) for k, v in by_cat.most_common()},
        "top_merchants": by_merchant.most_common(15),
        "weekday_spend": round(weekday_spend, 2),
        "weekend_spend": round(weekend, 2),
        "grocery_trips": sum(1 for t in txns if t["cat"] == "groceries"),
        "delivery_orders": sum(1 for t in txns if t["cat"] == "delivery"),
        "eating_out_count": lunch_hours,
        "distinct_merchants": len(by_merchant),
    }


def write_profile(txns, findings=None):
    facts = profile_facts(txns)

    prompt = f"""Spending facts (90 days, one account):

    {json.dumps(facts, indent=2)}

    Notable patterns already detected:
    {json.dumps(findings or [], indent=2)}

    Write the profile."""

    msg = ai.messages.create(
        model="claude-sonnet-5",
        max_tokens=400,
        system=PROFILE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    return msg.content[0].text.strip()


if __name__ == "__main__":
    with open("enriched.json") as f:
        txns = json.load(f)
    print(json.dumps(write_profile(txns), indent=2))