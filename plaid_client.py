import os
import plaid
from dotenv import load_dotenv
from plaid.api import plaid_api
from plaid.model.transactions_sync_request import TransactionsSyncRequest

load_dotenv()

ENVIRONMENTS = {"sandbox": plaid.Environment.Sandbox, "production": plaid.Environment.Production}


def client():
    env = os.environ.get("PLAID_ENV", "sandbox").lower()
    return plaid_api.PlaidApi(plaid.ApiClient(plaid.Configuration(
        host=ENVIRONMENTS[env],
        api_key={"clientId": os.environ["PLAID_CLIENT_ID"], "secret": os.environ["PLAID_SECRET"]},
    )))


def fetch_transactions():
    api = client()
    added, cursor = [], None
    while True:
        request = {"access_token": os.environ["PLAID_ACCESS_TOKEN"]}
        if cursor:
            request["cursor"] = cursor
        response = api.transactions_sync(TransactionsSyncRequest(**request))
        added.extend(t.to_dict() for t in response["added"])
        if not response["has_more"]:
            break
        cursor = response["next_cursor"]
    return {"added": added}


if __name__ == "__main__":
    for t in fetch_transactions()["added"][:5]:
        print(t["date"], t["amount"], t.get("merchant_name") or t["name"])
