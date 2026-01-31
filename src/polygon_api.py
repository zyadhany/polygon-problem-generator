import time
import hashlib
import random
import string
import os
from urllib.parse import urlsplit
import requests
from dotenv import load_dotenv
load_dotenv()

import time, hashlib, random, string
from urllib.parse import quote_plus, quote
import requests

def _build_query(items: list[tuple[str, str]], space_as_plus: bool) -> str:
    q = quote_plus if space_as_plus else quote  # '+' vs '%20' for spaces
    return "&".join(f"{q(k)}={q(v)}" for k, v in items)

# set these once

POLYGON_API_KEY = os.getenv("POLYGON_KEY") or os.getenv("POLYGON_API_KEY")
POLYGON_API_SECRET = os.getenv("POLYGON_SECRET") or os.getenv("POLYGON_API_SECRET")
POLYGON_BASE_URL = os.getenv("POLYGON_BASE_URL", "https://polygon.codeforces.com/api")

if not POLYGON_API_KEY or not POLYGON_API_SECRET:
    raise RuntimeError("Missing POLYGON_KEY/POLYGON_SECRET in environment")



def polygon_api_call(method_name: str, params: dict | None = None, timeout: int = 20) -> dict:
    url = f"{POLYGON_BASE_URL}/{method_name}"

    p = dict(params or {})
    p["apiKey"] = POLYGON_API_KEY
    p["time"] = str(int(time.time()))

    # sort by key then value (raw, decoded strings)
    items = sorted((str(k), str(v)) for k, v in p.items())

    rand = "".join(random.choices(string.digits, k=6))

    # IMPORTANT: signature string uses RAW values (no urlencode)
    param_str = "&".join(f"{k}={v}" for k, v in items)
    to_sign = f"{rand}/{method_name}?{param_str}#{POLYGON_API_SECRET}"
    api_sig = rand + hashlib.sha512(to_sign.encode("utf-8")).hexdigest()

    # send POST form
    data = dict(items)
    data["apiSig"] = api_sig

    r = requests.post(url, data=data, timeout=timeout)

    ctype = (r.headers.get("Content-Type") or "").lower()

    # Try JSON first (even if status_code != 200)
    if "application/json" in ctype or r.text.lstrip().startswith("{"):
        j = r.json()
        if j.get("status") != "OK":
            raise RuntimeError(j.get("comment", str(j)))
        return j.get("result", {})

    # Fallback: plain text / HTML
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text}")

    # Some endpoints may return plain text on success
    return r.text

if __name__ == "__main__":
    r = polygon_api_call("problems.list")
    print(len(r))
