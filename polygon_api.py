import time
import hashlib
import random
import string
import os
from urllib.parse import urlsplit
import requests

# set these once

POLYGON_API_KEY = os.environ["POLYGON_API_KEY"]
POLYGON_API_SECRET = os.environ["POLYGON_API_SECRET"]
POLYGON_BASE_URL = "https://polygon.codeforces.com/api"


def polygon_api_call(method_name: str, params: dict | None = None, timeout: int = 20) -> dict:
    url = f"{POLYGON_BASE_URL}/{method_name}"

    p = dict(params or {})
    p["apiKey"] = POLYGON_API_KEY
    p["time"] = int(time.time())

    # IMPORTANT: sort params for signing
    items = sorted(p.items())

    rand = "".join(random.choices(string.digits, k=6))

    prepped = requests.Request("GET", url, params=items).prepare()
    query = urlsplit(prepped.url).query  # sorted + encoded

    to_sign = f"{rand}/{method_name}?{query}#{POLYGON_API_SECRET}"
    api_sig = rand + hashlib.sha512(to_sign.encode("utf-8")).hexdigest()

    # send the SAME sorted params + apiSig
    r = requests.get(url, params=items + [("apiSig", api_sig)], timeout=timeout)
    return r.json()['result']

# test
if __name__ == "__main__":
    r = polygon_api_call("problem.create", {"name": "test-api"})
    print(len(r))
    # for k in r:
    #     print(k)