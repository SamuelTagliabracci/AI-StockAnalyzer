"""Claude Code — the scheduled premium analyst (R3, tier 1).

Claude Code itself is the model (no API key needed): on a schedule it reads the
analyst *bundle* for each symbol (quant scores + fundamentals + recent price action,
all from the shared pool), reasons about it, and writes a verdict to the
agent_verdicts ledger. Every verdict captures price_at_call + horizon so it becomes a
scoreable prediction later (R5).

Usage:
    python -m agents.claude_analyst bundle NVDA AAPL RY.TO     # print input bundles (JSON)
    python -m agents.claude_analyst write NVDA STRONG_BUY 0.78 200 12M "rationale..."

The `bundle` command is what Claude reads; `write` is how the verdict is persisted.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_manager import DatabaseManager

AGENT_NAME = "Claude Code"
MODEL_ID = "claude-opus-4-8"
DB_PATH = os.environ.get("MARKET_DB", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "market.db"))

# Fundamentals worth showing the analyst (skip the noisy/empty ones).
_FUND_KEYS = [
    "pe_ratio", "forward_pe", "peg_ratio", "price_to_book", "debt_to_equity",
    "roe", "profit_margin", "revenue_growth", "earnings_growth",
    "dividend_yield", "beta",
]


def _pct(a, b):
    """Percent change from b to a, rounded; None if not computable."""
    try:
        if a is None or not b:
            return None
        return round((a - b) / b * 100, 1)
    except (TypeError, ZeroDivisionError):
        return None


def bundle(db: DatabaseManager, symbol: str) -> dict:
    """Assemble everything Claude needs to form a verdict on one symbol."""
    comp = db.get_company(symbol) or {}
    analysis = db.get_latest_analysis(symbol) or {}
    fund = db.get_latest_fundamentals(symbol) or {}
    prices = db.get_price_data(symbol, days=260)

    closes, last, recent = [], None, {}
    if prices is not None and not prices.empty:
        closes = [float(c) for c in prices["close"].tolist() if c is not None]
        if closes:
            last = closes[-1]
            # Trading-day offsets ~ 21/63/126/252 = 1M/3M/6M/12M.
            recent = {
                "ret_1m_pct": _pct(last, closes[-22]) if len(closes) > 22 else None,
                "ret_3m_pct": _pct(last, closes[-64]) if len(closes) > 64 else None,
                "ret_6m_pct": _pct(last, closes[-127]) if len(closes) > 127 else None,
                "ret_12m_pct": _pct(last, closes[0]) if len(closes) > 200 else None,
                "high_252d": round(max(closes), 2),
                "low_252d": round(min(closes), 2),
            }

    return {
        "symbol": symbol,
        "name": comp.get("name") or symbol,
        "sector": comp.get("sector"),
        "industry": comp.get("industry"),
        "currency": comp.get("currency"),
        "exchange": comp.get("exchange"),
        "last_close": round(last, 2) if last else None,
        "as_of": str(prices["date"].iloc[-1])[:10] if (prices is not None and not prices.empty) else None,
        "recent": recent,
        "quant": {
            "recommendation": analysis.get("recommendation"),
            "total_score": analysis.get("total_score"),
            "fundamental_score": analysis.get("fundamental_score"),
            "technical_score": analysis.get("technical_score"),
            "momentum_score": analysis.get("momentum_score"),
            "risk_score": analysis.get("risk_score"),
            "target_price": analysis.get("target_price"),
        },
        "fundamentals": {k: fund.get(k) for k in _FUND_KEYS if fund.get(k) is not None},
    }


def write_verdict(db: DatabaseManager, symbol: str, action: str, confidence: float,
                  target_price, horizon: str, rationale: str) -> bool:
    """Persist a Claude verdict, stamping the price at call time for later scoring."""
    prices = db.get_price_data(symbol, days=2)
    price_at_call = float(prices["close"].iloc[-1]) if (prices is not None and not prices.empty) else None
    return db.add_agent_verdict({
        "agent": AGENT_NAME,
        "model": MODEL_ID,
        "symbol": symbol,
        "action": action.replace("_", " ").upper(),
        "confidence": float(confidence),
        "target_price": float(target_price) if target_price not in (None, "", "none") else None,
        "price_at_call": price_at_call,
        "horizon": horizon,
        "rationale": rationale,
    })


def _main(argv):
    db = DatabaseManager(DB_PATH)
    if len(argv) >= 2 and argv[0] == "bundle":
        print(json.dumps([bundle(db, s) for s in argv[1:]], indent=2, default=str))
    elif len(argv) == 6 and argv[0] == "write":
        _, symbol, action, conf, target, horizon = argv
        ok = write_verdict(db, symbol, action, float(conf), target, horizon, sys.stdin.read().strip() or "")
        print("ok" if ok else "FAILED")
    elif len(argv) == 7 and argv[0] == "write":
        _, symbol, action, conf, target, horizon, rationale = argv
        ok = write_verdict(db, symbol, action, float(conf), target, horizon, rationale)
        print("ok" if ok else "FAILED")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    _main(sys.argv[1:])
