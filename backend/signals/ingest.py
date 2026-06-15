"""Run smart-money signal ingesters across symbols and persist to market_signals.

Usage:
    python -m signals.ingest AAPL MSFT NVDA JPM XOM      # all sources
    python -m signals.ingest --source insider AAPL MSFT  # one source
    python -m signals.ingest                             # defaults to the 10 starters
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_manager import DatabaseManager
from signals import insider, institution, congress, copytrade

DB_PATH = os.environ.get("MARKET_DB", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "market.db"))

SOURCES = {
    "insider": insider.ingest,
    "institution": institution.ingest,
    "congress": congress.ingest,
    "copytrade": copytrade.ingest,
}

STARTERS = ["AAPL", "MSFT", "NVDA", "JPM", "XOM",
            "RY.TO", "TD.TO", "CNQ.TO", "ENB.TO", "SHOP.TO"]


def _main(argv):
    source = None
    if len(argv) >= 2 and argv[0] == "--source":
        source = argv[1]
        argv = argv[2:]
    symbols = argv or STARTERS
    db = DatabaseManager(DB_PATH)

    sources = {source: SOURCES[source]} if source else SOURCES
    if source and source not in SOURCES:
        print(f"unknown source {source!r}; pick from {list(SOURCES)}")
        sys.exit(1)

    total = 0
    for name, fn in sources.items():
        print(f"[{name}] ingesting {len(symbols)} symbol(s)...")
        n = fn(db, symbols)
        print(f"[{name}] {n} new signal(s)")
        total += n
    print(f"done — {total} new signal(s) total")


if __name__ == "__main__":
    _main(sys.argv[1:])
