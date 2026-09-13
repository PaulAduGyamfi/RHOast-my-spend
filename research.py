import os, json
from dotenv import load_dotenv
from typing import Literal
from pydantic import BaseModel
from tavily import TavilyClient
from anthropic import Anthropic

load_dotenv()

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
ai = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

CACHE_PATH = "cache.json"
def load_cache():
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("cache.json unreadable, starting fresh")
        return {}

_cache = load_cache()

class MerchantExtraction(BaseModel):
    name: str | None
    cat: Literal["delivery", "streaming", "fitness", "groceries", 
    "dining","transport","transport","retail",
    "software", "medical", "pharmacy", "legal",
    "childcare", "lender", "religious", "charity", "adult", "recovery", "unknown"]
    note: str
    confidence: Literal["high","low"]

def research(merchant):
    if merchant in _cache:
        print("---read from cache----")
        return _cache[merchant]

    hits = tavily_client.search(f'"{merchant}" company what do they sell',
                     max_results=3)
    blob = "\n".join(h["content"][:500] for h in hits["results"])

    prompt = f"""Merchant name from a bank statement: "{merchant}"
                Web search results:
                {blob}
                Return ONLY JSON, no markdown fences:
                {{"name": "proper company name or null if unclear",
                "cat": "one of: delivery, streaming, fitness, groceries, dining,
                        transport, retail, software, medical, pharmacy, legal,
                        childcare, lender, religious, charity, adult, recovery, unknown",
                "note": "one plain sentence on what they actually sell",
                "confidence": "high|low"}}"""

    msg = ai.messages.parse(
        model="claude-sonnet-5", max_tokens=300,
        messages=[{"role":"user","content":prompt}],
        output_format=MerchantExtraction)

    entry = msg.parsed_output.model_dump()
    
    _cache[merchant] = entry

    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_cache, f, indent=2)
    
    os.replace(tmp, CACHE_PATH)

    return entry


if __name__ == "__main__":
    print(research("burger king"))