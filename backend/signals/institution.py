"""Institutional holdings via SEC 13F — STUB.

Funds managing >$100M report holdings quarterly (45-day lag) on Form 13F. The data is
free on EDGAR, but the info tables key holdings by CUSIP, not ticker — so a real
implementation needs a CUSIP→ticker map (e.g. an OpenFIGI lookup) plus a curated list of
famous-fund CIKs (Berkshire, Bridgewater, Citadel, ...) to diff quarter-over-quarter into
BUY/SELL deltas. Schema + feed slot are ready; wire the CUSIP map to light this up.
"""


def ingest(db, symbols, **_) -> int:
    print("  [institution] STUB — needs CUSIP→ticker map + curated fund CIKs; 0 written")
    return 0
