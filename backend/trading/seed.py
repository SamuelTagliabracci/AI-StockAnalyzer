"""Create the trading accounts: Sam (human) + one autonomous agent per AI analyst.

Idempotent — safe to re-run. Agents start with $10k USD paper each (they trade US names;
see trader_loop). Sam gets empty CAD + USD wallets to fill in manually (his Wealthsimple
cash/holdings) via the UI. Run: python -m trading.seed
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_manager import DatabaseManager

DB_PATH = os.environ.get("MARKET_DB", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "market.db"))

HUMAN = {"display_name": "Sam", "email": "sam@cornelltech.ca"}
# agent_key MUST match the agent name written into agent_verdicts.
AGENTS = [
    {"display_name": "Claude Code", "agent_key": "Claude Code"},
    {"display_name": "Qwen2.5 7B", "agent_key": "Qwen2.5 7B"},
    {"display_name": "Llama 3.1 8B", "agent_key": "Llama 3.1 8B"},
]
AGENT_START_USD = 10_000.0
# New human users start with $10k USD paper to play with (CAD wallet created at 0; set it
# via My Portfolio → Manual entry to trade TSX names). They can overwrite to mirror real
# brokerage cash anytime. Only granted on brand-new wallets, never clobbering edits.
HUMAN_START_USD = 10_000.0


def seed(db: DatabaseManager) -> None:
    # Human account — grant the starting balance only on first creation.
    human = db.get_or_create_account("human", HUMAN["display_name"], email=HUMAN["email"])
    existing = db.get_cash(human["id"])
    if "USD" not in existing:
        db.set_cash(human["id"], "USD", HUMAN_START_USD)
    if "CAD" not in existing:
        db.set_cash(human["id"], "CAD", 0.0)
    print(f"human: {human['display_name']} (id={human['id']}) cash={db.get_cash(human['id'])}")

    # Agent accounts — $10k USD each, only on first creation.
    for a in AGENTS:
        acct = db.get_or_create_account("agent", a["display_name"], agent_key=a["agent_key"])
        if "USD" not in db.get_cash(acct["id"]):
            db.set_cash(acct["id"], "USD", AGENT_START_USD)
        print(f"agent: {acct['display_name']} (id={acct['id']}) cash={db.get_cash(acct['id'])}")


if __name__ == "__main__":
    seed(DatabaseManager(DB_PATH))
    print("done")
