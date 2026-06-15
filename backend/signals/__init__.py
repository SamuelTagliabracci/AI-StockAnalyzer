"""Smart-money signal ingesters — real disclosed trades by the big players.

Each source module exposes `ingest(db, symbols) -> int` (rows written) and writes to the
shared `market_signals` table, so the Smart Money feed treats them uniformly:

  insider       (SEC Form 4)   — LIVE: corporate insiders, ~2-day filing lag.
  institution   (SEC 13F)      — STUB: needs CUSIP→ticker mapping; quarterly, 45-day lag.
  congress      (STOCK Act)    — STUB: free community feeds went dark; needs an API key.
  copytrade     (eToro etc.)   — STUB: no official free API; scraping is ToS-sensitive.

Coverage note: SEC sources only cover US issuers. Canadian (.TO) insiders file with
SEDI, which has no clean API — so TSX names are sparse/empty until a SEDI source is added.
"""
