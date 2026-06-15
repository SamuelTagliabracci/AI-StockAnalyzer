"""Refresh the shared data pool from Yahoo Finance.

The seed DB drifts: the legacy TSX names (originally seeded with no exchange tag) had
prices frozen at 2025-09-03, while the US names stayed roughly current. This brings
everything up to the latest close and re-tags any company missing exchange/currency.

Usage:
    python -m backfill prices     # incremental price update for every company
    python -m backfill retag      # re-fetch company info for un-tagged (exchange IS NULL) names
    python -m backfill all        # retag first (so new tags land), then prices
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager
from data_ingestion_manager import DataIngestionManager

DB_PATH = os.environ.get("MARKET_DB", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "market.db"))


def _reset_throttle(db: DatabaseManager) -> None:
    """Clear any stuck rate-limit state from a prior run so the loop runs clean."""
    db.set_system_setting("daily_limit_reached", "false")
    db.set_system_setting("rate_limit_delay", "1")


def _untagged_symbols(db: DatabaseManager) -> list:
    """Symbols whose exchange tag is missing. Queried via SQL, not get_all_companies():
    pandas turns SQL NULL into NaN (which is truthy), so a `not exchange` test misses them.
    """
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM companies "
                    "WHERE exchange IS NULL OR TRIM(exchange) = '' ORDER BY symbol")
        return [r[0] for r in cur.fetchall()]


def retag(db: DatabaseManager, ing: DataIngestionManager) -> int:
    """Re-fetch company info for names with no exchange tag (the legacy TSX seed)."""
    syms = _untagged_symbols(db)
    print(f"[retag] {len(syms)} untagged compan(ies)")
    fixed = 0
    for i, sym in enumerate(syms):
        info = ing.get_company_info(sym)
        if info and info.get("exchange"):
            db.add_company(info)
            fixed += 1
            print(f"  ✓ {sym:10} → {info.get('exchange')} / {info.get('currency')}")
        else:
            print(f"  ✗ {sym:10} no info", file=sys.stderr)
        if (i + 1) % 10 == 0:
            print(f"  …{i + 1}/{len(syms)}")
    print(f"[retag] tagged {fixed}/{len(syms)}")
    return fixed


def prices(db: DatabaseManager, ing: DataIngestionManager) -> dict:
    """Incremental price update for every company (only fetches bars since last close)."""
    companies = db.get_all_companies(active_only=False)
    print(f"[prices] updating {len(companies)} compan(ies)")
    ok = fail = 0
    for i, c in enumerate(companies):
        sym = c["symbol"]
        before = db.get_latest_price_date(sym)
        try:
            updated = ing.update_price_data(sym)
        except Exception as e:  # one bad symbol must not sink the run
            print(f"  ! {sym}: {e}", file=sys.stderr)
            updated = False
        after = db.get_latest_price_date(sym)
        if after != before:
            ok += 1
            print(f"  ✓ {sym:10} {before} → {after}")
        elif updated:
            ok += 1  # already current
        else:
            fail += 1
            print(f"  · {sym:10} unchanged ({before})", file=sys.stderr)
        if (i + 1) % 20 == 0:
            print(f"  …{i + 1}/{len(companies)}")
    print(f"[prices] advanced/current: {ok}, no-data: {fail}")
    return {"ok": ok, "fail": fail}


def _main(argv):
    mode = argv[0] if argv else "all"
    db = DatabaseManager(DB_PATH)
    ing = DataIngestionManager(db)
    _reset_throttle(db)
    t0 = time.time()
    if mode in ("retag", "all"):
        retag(db, ing)
    if mode in ("prices", "all"):
        prices(db, ing)
    if mode not in ("retag", "prices", "all"):
        print(__doc__); sys.exit(1)
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    _main(sys.argv[1:])
