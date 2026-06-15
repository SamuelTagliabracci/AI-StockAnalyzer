"""Market-wide sentiment: CNN Fear & Greed Index.

Unlike the per-symbol smart-money signals (see signals/), this is a single market-wide
gauge (0-100) plus the seven sub-indicators CNN derives it from. We fetch CNN's public
dataviz endpoint, which needs full browser-looking headers or it answers 418.

Exposes `fetch_fear_greed() -> dict` in the camelCase shape the frontend renders.
"""
import json
import time
import urllib.request

URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

# How many trailing daily points to ship for the sparkline (~3 trading months).
_HISTORY_POINTS = 60

# CNN's endpoint 418s without a believable browser fingerprint.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.cnn.com/",
    "Origin": "https://www.cnn.com",
}

# The seven component gauges, in the order CNN presents them. (CNN ships two VIX and
# two momentum series; we keep the headline one of each.) key -> human label.
_COMPONENTS = [
    ("market_momentum_sp500", "Market Momentum"),
    ("stock_price_strength", "Stock Price Strength"),
    ("stock_price_breadth", "Stock Price Breadth"),
    ("put_call_options", "Put/Call Options"),
    ("market_volatility_vix", "Market Volatility"),
    ("junk_bond_demand", "Junk Bond Demand"),
    ("safe_haven_demand", "Safe Haven Demand"),
]


def _round(x):
    return round(x, 1) if isinstance(x, (int, float)) else None


def fetch_fear_greed(timeout: int = 20) -> dict:
    """Fetch the live CNN Fear & Greed Index. Raises on network/parse failure."""
    req = urllib.request.Request(URL, headers=_HEADERS)
    data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    fg = data["fear_and_greed"]
    components = []
    for key, label in _COMPONENTS:
        c = data.get(key) or {}
        if "score" in c:
            components.append({"key": key, "label": label,
                               "score": _round(c.get("score")), "rating": c.get("rating")})
    # Trailing daily series for the sparkline: oldest → newest, rounded to ints.
    hist = ((data.get("fear_and_greed_historical") or {}).get("data")) or []
    history = [round(p["y"]) for p in hist[-_HISTORY_POINTS:] if isinstance(p.get("y"), (int, float))]
    return {
        "score": _round(fg.get("score")),
        "rating": fg.get("rating"),  # e.g. 'fear', 'greed', 'extreme fear'
        "timestamp": fg.get("timestamp"),
        "previousClose": _round(fg.get("previous_close")),
        "previous1Week": _round(fg.get("previous_1_week")),
        "previous1Month": _round(fg.get("previous_1_month")),
        "previous1Year": _round(fg.get("previous_1_year")),
        "components": components,
        "history": history,
    }


# --- Cached, never-raising accessor for the analyst/trader paths ----------------
# bundle() is called once per symbol in a loop and the trader loop runs unattended, so
# they must not hammer CNN or crash on a network blip. Cache the brief read in-process.
_BRIEF_TTL = 600  # seconds
_brief_cache = {"at": 0.0, "val": None}


def fear_greed_brief(timeout: int = 10):
    """{'score', 'rating'} for prompts/trading — cached ~10 min, returns None if never fetched.

    Never raises: on a failed fetch it keeps serving the last good value (or None).
    """
    now = time.monotonic()
    if _brief_cache["val"] is not None and now - _brief_cache["at"] < _BRIEF_TTL:
        return _brief_cache["val"]
    try:
        d = fetch_fear_greed(timeout=timeout)
        _brief_cache.update(at=now, val={"score": d["score"], "rating": d["rating"]})
    except Exception:
        _brief_cache["at"] = now  # back off even on failure; keep last good val
    return _brief_cache["val"]


if __name__ == "__main__":
    import pprint
    pprint.pp(fetch_fear_greed())
