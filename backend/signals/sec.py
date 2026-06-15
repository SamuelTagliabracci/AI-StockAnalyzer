"""Shared SEC EDGAR helpers: polite HTTP + ticker→CIK resolution.

SEC asks for a descriptive User-Agent with contact info and rate-limits to ~10 req/s;
we stay well under that. CIKs are cached per process after the first lookup.
"""
import json
import os
import time
import urllib.request

UA = os.environ.get("SEC_USER_AGENT", "AI-StockMarket research sam@cornelltech.ca")
_HEADERS = {"User-Agent": UA}
_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"

_cik_cache: dict = {}
_last_call = [0.0]


def get(url: str, timeout: int = 20) -> bytes:
    """GET with SEC's required headers and a gentle ~7 req/s throttle."""
    wait = 0.15 - (time.monotonic() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        data = urllib.request.urlopen(req, timeout=timeout).read()
    finally:
        _last_call[0] = time.monotonic()
    return data


def cik_for(ticker: str) -> str | None:
    """Resolve a US ticker to its zero-padded 10-digit CIK, or None if not found.

    Strips exchange suffixes (RY.TO → RY) so callers can pass app symbols directly.
    """
    base = ticker.split(".")[0].upper()
    if not _cik_cache:
        rows = json.loads(get(_TICKER_MAP_URL))
        for r in rows.values():
            _cik_cache[r["ticker"].upper()] = str(r["cik_str"]).zfill(10)
    return _cik_cache.get(base)
