from typing import Literal, get_args

Category = Literal[
    "alcohol", "coffee", "delivery", "education", "fitness", "fuel", "gaming",
    "groceries", "pet", "restaurant", "retail", "rideshare", "software",
    "streaming", "subscription", "telecom", "transit", "travel", "utilities",
    "bank fee", "late fee", "cash", "transfer",
    "adult", "charity", "childcare", "legal", "lender", "medical", "pharmacy",
    "recovery", "religious",
    "unknown",
]

CATEGORIES = get_args(Category)

SENSITIVE_CATS = {"medical", "pharmacy", "legal", "childcare", "lender",
                  "religious", "charity", "adult", "recovery"}
FEE_CATS = {"bank fee", "late fee"}
EATING_OUT_CATS = {"restaurant", "coffee", "delivery"}
