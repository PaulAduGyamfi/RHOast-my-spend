import os
from dotenv import load_dotenv
from tavily import TavilyClient
import requests
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_sync_request import TransactionsSyncRequest

load_dotenv()

"""
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
response = tavily_client.search("Who is Leo Messi?")

print(response)

"""


"""client = plaid_api.PlaidApi(plaid.ApiClient(plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={"clientId": os.environ["PLAID_CLIENT_ID"],
             "secret": os.environ["PLAID_SECRET"]},
)))

r = client.transactions_sync(TransactionsSyncRequest(
    access_token=os.environ["PLAID_ACCESS_TOKEN"],
    count=5,
))

print("plaid ok:", len(r["added"]), "transactions")
for t in r["added"][:5]:
    print(t["date"], t["amount"], t["name"])"""

r = requests.get("https://api.elevenlabs.io/v1/voices",
                 headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]})
print("elevenlabs ok:", r.status_code, r.json()["voices"][0]["name"],
      r.json()["voices"][0]["voice_id"])