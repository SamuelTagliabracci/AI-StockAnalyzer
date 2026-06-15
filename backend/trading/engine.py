"""Paper-trade execution + portfolio valuation.

Fills happen at the latest close (we have daily data; intraday is Phase 4). A trade in a
stock draws from / credits the wallet in that stock's own currency — no FX at trade time.
For cross-currency leaderboards we report a USD-equivalent total using a fixed reference
rate (clearly approximate, not a live FX feed).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_manager import DatabaseManager

# Approximate reference rate for the leaderboard's USD-equiv total only. Not used for fills.
CAD_PER_USD = 1.37


def price_of(db: DatabaseManager, symbol: str):
    """(latest_close, currency) for a symbol; (None, None) if no price."""
    df = db.get_price_data(symbol, days=2)
    if df is None or df.empty:
        return None, None
    price = float(df.iloc[-1]["close"])
    comp = db.get_company(symbol) or {}
    currency = comp.get("currency") or ("CAD" if symbol.upper().endswith((".TO", ".V", ".CN", ".NE")) else "USD")
    return price, currency


def execute_order(db: DatabaseManager, account_id: int, symbol: str, side: str,
                  shares: float, kind: str = "paper", rationale: str = None) -> dict:
    """Execute one order against an account. Returns {ok, message, ...fill}.

    BUY draws from the stock-currency wallet (rejects on insufficient cash); SELL requires
    enough shares. Holdings track a running average cost; cash moves by notional.
    """
    side = side.upper()
    try:
        shares = float(shares)
    except (TypeError, ValueError):
        return {"ok": False, "message": "Invalid share quantity."}
    if shares <= 0:
        return {"ok": False, "message": "Share quantity must be positive."}
    if side not in ("BUY", "SELL"):
        return {"ok": False, "message": f"Unknown side {side!r}."}

    price, currency = price_of(db, symbol)
    if price is None:
        return {"ok": False, "message": f"No price available for {symbol}."}

    notional = shares * price
    holding = db.get_holding(account_id, symbol)

    if side == "BUY":
        cash = db.get_cash(account_id).get(currency, 0.0)
        if cash + 1e-6 < notional:
            return {"ok": False, "message": f"Insufficient {currency} cash: have {cash:,.2f}, need {notional:,.2f}."}
        old_shares = float(holding["shares"]) if holding else 0.0
        old_avg = float(holding["avg_cost"]) if holding else 0.0
        new_shares = old_shares + shares
        new_avg = (old_shares * old_avg + notional) / new_shares
        db.adjust_cash(account_id, currency, -notional)
        db.upsert_holding(account_id, symbol, new_shares, new_avg, currency)
    else:  # SELL
        if not holding or float(holding["shares"]) + 1e-6 < shares:
            have = float(holding["shares"]) if holding else 0.0
            return {"ok": False, "message": f"Not enough shares of {symbol}: have {have}, sell {shares}."}
        new_shares = float(holding["shares"]) - shares
        db.adjust_cash(account_id, currency, notional)
        db.upsert_holding(account_id, symbol, new_shares, float(holding["avg_cost"]), currency)

    db.add_trade({
        "account_id": account_id, "symbol": symbol, "side": side, "shares": shares,
        "price": price, "currency": currency, "kind": kind, "rationale": rationale,
    })
    return {"ok": True, "message": f"{side} {shares:g} {symbol} @ {price:,.2f} {currency}",
            "symbol": symbol, "side": side, "shares": shares, "price": price, "currency": currency}


def value_portfolio(db: DatabaseManager, account_id: int) -> dict:
    """Mark-to-market valuation: cash + positions per currency, P&L, USD-equiv total."""
    cash = db.get_cash(account_id)
    positions = []
    holdings_value = {}  # currency -> market value of positions
    for h in db.get_holdings(account_id):
        price, currency = price_of(db, h["symbol"])
        currency = currency or h.get("currency") or "USD"
        shares, avg = float(h["shares"]), float(h["avg_cost"])
        mkt = (price or avg) * shares
        cost = avg * shares
        pnl = mkt - cost
        positions.append({
            "symbol": h["symbol"], "shares": shares, "avgCost": avg,
            "price": price, "currency": currency,
            "marketValue": mkt, "costBasis": cost,
            "unrealizedPnl": pnl, "unrealizedPnlPct": (pnl / cost * 100) if cost else 0.0,
        })
        holdings_value[currency] = holdings_value.get(currency, 0.0) + mkt

    # Per-currency totals (cash + positions) and a single USD-equivalent for ranking.
    currencies = set(cash) | set(holdings_value)
    by_currency = {
        cur: {"cash": cash.get(cur, 0.0), "positions": holdings_value.get(cur, 0.0),
              "total": cash.get(cur, 0.0) + holdings_value.get(cur, 0.0)}
        for cur in currencies
    }
    usd_equiv = 0.0
    for cur, v in by_currency.items():
        usd_equiv += v["total"] / CAD_PER_USD if cur == "CAD" else v["total"]

    total_cost = sum(p["costBasis"] for p in positions)
    total_unreal = sum(p["unrealizedPnl"] for p in positions)
    return {
        "accountId": account_id,
        "cash": cash,
        "positions": sorted(positions, key=lambda p: -p["marketValue"]),
        "byCurrency": by_currency,
        "totalUsdEquiv": usd_equiv,
        "unrealizedPnl": total_unreal,
        "unrealizedPnlPct": (total_unreal / total_cost * 100) if total_cost else 0.0,
    }
