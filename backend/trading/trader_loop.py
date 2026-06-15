"""Autonomous AI paper-trader loop.

Each AI agent trades its own $10k (USD) book fully autonomously — no human approval. On
each cycle, per agent:
  1. (ollama agents) re-analyze its US universe → fresh verdicts in agent_verdicts.
  2. Read its latest verdicts, map each action → a target weight of equity.
  3. Rebalance toward those targets via the paper engine (sells first to free cash,
     then buys by confidence until cash runs out).

Agents trade USD names only (their wallet is USD), sidestepping FX. Claude Code can't
self-run server-side (no API key), so it trades on whatever verdicts already exist.

Usage:
    python -m trading.trader_loop once          # run one cycle for all agents now
    python -m trading.trader_loop loop          # run forever, ~3×/day (every 8h)
    python -m trading.trader_loop once --agent "Qwen2.5 7B"
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_manager import DatabaseManager
from trading.engine import execute_order, value_portfolio, price_of
from market_sentiment import fear_greed_brief

DB_PATH = os.environ.get("MARKET_DB", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "market.db"))

# Action → target portfolio weight for that name. None = leave position untouched.
TARGET_WEIGHT = {
    "STRONG BUY": 0.25, "BUY": 0.12, "MODERATE BUY": 0.12,
    "HOLD": None, "WEAK HOLD": None,
    "CONSIDER SELLING": 0.0, "SELL": 0.0, "STRONG SELL": 0.0,
}

# agent_key → ollama model id (for the re-analyze step). Claude has no local model.
AGENT_MODEL = {"Qwen2.5 7B": "qwen2.5:7b", "Llama 3.1 8B": "llama3.1:8b"}

# The US universe agents re-analyze + trade (USD wallet → USD names only).
US_UNIVERSE = ["AAPL", "MSFT", "NVDA", "JPM", "XOM"]

REBALANCE_MIN_USD = 25.0  # ignore tiny target/position gaps
SECONDS_PER_CYCLE = 8 * 3600  # ~3×/day


def _exposure_tilt(score):
    """Contrarian sentiment tilt → a multiplier on every buy target weight.

    Hunt when the crowd is fearful, trim exposure (hold more cash) when it's greedy.
    Sells are unaffected (their target weight is already 0). Returns (mult, stance).
    """
    if score is None:
        return 1.0, "sentiment n/a"
    if score < 25:
        return 1.30, f"F&G {score:.0f} extreme fear → hunt (×1.30)"
    if score < 45:
        return 1.15, f"F&G {score:.0f} fear → lean in (×1.15)"
    if score <= 55:
        return 1.0, f"F&G {score:.0f} neutral (×1.00)"
    if score <= 75:
        return 0.85, f"F&G {score:.0f} greed → cautious (×0.85)"
    return 0.70, f"F&G {score:.0f} extreme greed → defensive (×0.70)"


def _reanalyze(db, agent_key):
    """Refresh an ollama agent's verdicts before it trades. No-op for Claude."""
    model = AGENT_MODEL.get(agent_key)
    if not model:
        return
    try:
        from agents.ollama_analyst import run as ollama_run
        ollama_run(db, model, US_UNIVERSE)
    except Exception as e:
        print(f"  ! re-analyze {agent_key} failed: {e}", file=sys.stderr)


def trade_for_agent(db: DatabaseManager, account: dict, reanalyze: bool = True,
                    exposure: float = 1.0, fg_score=None) -> int:
    """Run one rebalance cycle for one agent account. Returns # of fills.

    `exposure` scales every buy target weight (the contrarian Fear & Greed tilt).
    """
    agent_key = account.get("agent_key")
    aid = account["id"]
    print(f"[{account['display_name']}] cycle…")
    if reanalyze:
        _reanalyze(db, agent_key)

    verdicts = db.get_all_latest_agent_verdicts()
    # Gather this agent's latest verdict per USD symbol.
    targets = {}  # symbol -> (weight, action, confidence)
    for sym, rows in verdicts.items():
        for v in rows:
            if v.get("agent") != agent_key:
                continue
            price, currency = price_of(db, sym)
            if currency != "USD" or price is None:
                continue
            weight = TARGET_WEIGHT.get((v.get("action") or "").upper())
            if weight is None:
                continue  # HOLD / unknown → leave as-is
            targets[sym] = (weight, v.get("action"), v.get("confidence") or 0)

    if not targets:
        print("  no actionable USD verdicts")
        return 0

    equity = value_portfolio(db, aid)["totalUsdEquiv"]
    holdings = {h["symbol"]: float(h["shares"]) for h in db.get_holdings(aid)}

    # Build orders: target value vs current value → buy/sell shares.
    orders = []  # (side, symbol, shares, confidence, action)
    for sym, (weight, action, conf) in targets.items():
        price, _ = price_of(db, sym)
        cur_shares = holdings.get(sym, 0.0)
        cur_val = cur_shares * price
        # Apply the sentiment tilt to buy targets only (weight 0 = sell stays a full exit).
        tgt_val = weight * equity * (exposure if weight > 0 else 1.0)
        diff = tgt_val - cur_val
        if abs(diff) < REBALANCE_MIN_USD:
            continue
        if diff > 0:
            orders.append(("BUY", sym, diff / price, conf, action))
        else:
            orders.append(("SELL", sym, min(cur_shares, -diff / price), conf, action))

    # Sells first (free cash), then buys by confidence (best ideas funded first).
    orders.sort(key=lambda o: (o[0] != "SELL", -o[3]))
    fills = 0
    for side, sym, shares, _conf, action in orders:
        if shares <= 0:
            continue
        tag = f" · F&G{fg_score:.0f}×{exposure:.2f}" if (fg_score is not None and side == "BUY") else ""
        res = execute_order(db, aid, sym, side, round(shares, 4),
                            rationale=f"auto: {action}{tag}")
        flag = "✓" if res["ok"] else "✗"
        print(f"  {flag} {side} {shares:.2f} {sym}: {res['message']}")
        if res["ok"]:
            fills += 1
    return fills


def run_cycle(db: DatabaseManager, only_agent: str = None, reanalyze: bool = True) -> None:
    agents = [a for a in db.list_accounts() if a["type"] == "agent"]
    if only_agent:
        agents = [a for a in agents if a["display_name"] == only_agent]
    # One sentiment read drives the whole cycle's exposure tilt.
    brief = fear_greed_brief()
    score = brief["score"] if brief else None
    exposure, stance = _exposure_tilt(score)
    print(f"market sentiment: {stance}")
    for a in agents:
        trade_for_agent(db, a, reanalyze=reanalyze, exposure=exposure, fg_score=score)
    print("--- leaderboard ---")
    for a in sorted(agents, key=lambda x: -value_portfolio(db, x["id"])["totalUsdEquiv"]):
        v = value_portfolio(db, a["id"])
        print(f"  {a['display_name']:<14} ${v['totalUsdEquiv']:,.2f}  "
              f"(unreal {v['unrealizedPnl']:+,.2f})  {len(v['positions'])} pos")


def _main(argv):
    mode = argv[0] if argv else "once"
    only = None
    if "--agent" in argv:
        only = argv[argv.index("--agent") + 1]
    no_reanalyze = "--no-reanalyze" in argv
    db = DatabaseManager(DB_PATH)
    if mode == "once":
        run_cycle(db, only_agent=only, reanalyze=not no_reanalyze)
    elif mode == "loop":
        while True:
            run_cycle(db, only_agent=only, reanalyze=not no_reanalyze)
            print(f"sleeping {SECONDS_PER_CYCLE/3600:.0f}h until next cycle…")
            time.sleep(SECONDS_PER_CYCLE)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    _main(sys.argv[1:])
