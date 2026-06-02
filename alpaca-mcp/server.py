"""
Alpaca MCP server — paper-trading, locked down.

Exposes a Tradier-style tool surface (account, positions, quotes, bars, orders)
over Alpaca's API so an LLM (Claude) can read the account and place trades.

SAFETY (read before flipping anything):
  * PAPER is hardcoded True below. Real money is impossible until you change it.
  * Every order is checked against MAX_ORDER_NOTIONAL (default $25) so the model
    can't blow the account on one trade. Reject-by-default if price is unknown.
  * Handles both US stocks ("AAPL") and crypto ("BTC/USD"). A "/" in the symbol
    means crypto.

Set credentials via env vars (paper keys from https://app.alpaca.markets/paper):
  ALPACA_API_KEY, ALPACA_SECRET_KEY
Optional:
  MAX_ORDER_NOTIONAL  (default 25)   max $ per single order
"""

import os

from mcp.server.fastmcp import FastMCP

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import (
    StockLatestQuoteRequest,
    CryptoLatestQuoteRequest,
    StockBarsRequest,
    CryptoBarsRequest,
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# ---------------------------------------------------------------------------
# Config & guardrails
# ---------------------------------------------------------------------------
PAPER = True  # <-- hardcoded. Do NOT change without reading the README.
API_KEY = os.environ.get("ALPACA_API_KEY", "")
SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")
MAX_ORDER_NOTIONAL = float(os.environ.get("MAX_ORDER_NOTIONAL", "25"))

if not API_KEY or not SECRET_KEY:
    raise SystemExit(
        "Missing ALPACA_API_KEY / ALPACA_SECRET_KEY env vars. "
        "Get paper keys at https://app.alpaca.markets/paper"
    )

mcp = FastMCP("alpaca")

trading = TradingClient(API_KEY, SECRET_KEY, paper=PAPER)
stock_data = StockHistoricalDataClient(API_KEY, SECRET_KEY)
crypto_data = CryptoHistoricalDataClient(API_KEY, SECRET_KEY)


def _is_crypto(symbol: str) -> bool:
    return "/" in symbol


def _latest_price(symbol: str) -> float | None:
    """Best-effort latest price for notional checks. None if unavailable."""
    try:
        if _is_crypto(symbol):
            q = crypto_data.get_crypto_latest_quote(
                CryptoLatestQuoteRequest(symbol_or_symbols=symbol)
            )[symbol]
        else:
            q = stock_data.get_stock_latest_quote(
                StockLatestQuoteRequest(symbol_or_symbols=symbol)
            )[symbol]
        # ask price if present, else bid
        return float(q.ask_price or q.bid_price) or None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Tools — account & positions
# ---------------------------------------------------------------------------
@mcp.tool()
def get_account() -> str:
    """Account summary: cash, buying power, equity, P&L. Paper account."""
    a = trading.get_account()
    return (
        f"PAPER account {a.account_number}\n"
        f"  status:        {a.status}\n"
        f"  cash:          ${a.cash}\n"
        f"  buying_power:  ${a.buying_power}\n"
        f"  equity:        ${a.equity}\n"
        f"  last_equity:   ${a.last_equity}\n"
        f"  daytrades(5d): {a.daytrade_count} (PDT-flagged: {a.pattern_day_trader})"
    )


@mcp.tool()
def get_positions() -> str:
    """All open positions with quantity, market value, and unrealized P&L."""
    positions = trading.get_all_positions()
    if not positions:
        return "No open positions."
    lines = []
    for p in positions:
        lines.append(
            f"{p.symbol}: {p.qty} @ avg ${p.avg_entry_price} | "
            f"mkt ${p.market_value} | uPL ${p.unrealized_pl} ({p.unrealized_plpc})"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tools — market data
# ---------------------------------------------------------------------------
@mcp.tool()
def get_quote(symbol: str) -> str:
    """Latest bid/ask quote. Stocks use 'AAPL', crypto uses 'BTC/USD'."""
    if _is_crypto(symbol):
        q = crypto_data.get_crypto_latest_quote(
            CryptoLatestQuoteRequest(symbol_or_symbols=symbol)
        )[symbol]
    else:
        q = stock_data.get_stock_latest_quote(
            StockLatestQuoteRequest(symbol_or_symbols=symbol)
        )[symbol]
    return f"{symbol}: bid ${q.bid_price} x{q.bid_size} | ask ${q.ask_price} x{q.ask_size}"


@mcp.tool()
def get_bars(symbol: str, timeframe: str = "1Hour", limit: int = 50) -> str:
    """Recent OHLCV candles for the model to reason on.

    timeframe: one of 1Min, 5Min, 15Min, 1Hour, 1Day. limit: number of bars.
    Stocks use 'AAPL', crypto uses 'BTC/USD'.
    """
    tf_map = {
        "1Min": TimeFrame(1, TimeFrameUnit.Minute),
        "5Min": TimeFrame(5, TimeFrameUnit.Minute),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
        "1Day": TimeFrame(1, TimeFrameUnit.Day),
    }
    tf = tf_map.get(timeframe, TimeFrame(1, TimeFrameUnit.Hour))
    if _is_crypto(symbol):
        req = CryptoBarsRequest(symbol_or_symbols=symbol, timeframe=tf, limit=limit)
        bars = crypto_data.get_crypto_bars(req)
    else:
        req = StockBarsRequest(symbol_or_symbols=symbol, timeframe=tf, limit=limit)
        bars = stock_data.get_stock_bars(req)
    rows = bars.data.get(symbol, [])
    if not rows:
        return f"No bars for {symbol}."
    out = [f"{symbol} {timeframe} (last {len(rows)} bars): t,o,h,l,c,v"]
    for b in rows:
        out.append(
            f"{b.timestamp:%Y-%m-%d %H:%M},{b.open},{b.high},{b.low},{b.close},{b.volume}"
        )
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Tools — orders
# ---------------------------------------------------------------------------
@mcp.tool()
def submit_order(
    symbol: str,
    qty: float,
    side: str,
    order_type: str = "market",
    limit_price: float | None = None,
) -> str:
    """Place an order (PAPER). side: 'buy' or 'sell'. order_type: 'market' or 'limit'.

    Guardrail: rejected if estimated notional exceeds MAX_ORDER_NOTIONAL
    (default $25). Stocks use 'AAPL', crypto uses 'BTC/USD'.
    """
    # --- notional guardrail ---
    est_price = limit_price if (order_type == "limit" and limit_price) else _latest_price(symbol)
    if est_price is None:
        return (
            f"REJECTED: could not determine a price for {symbol}, so the "
            f"${MAX_ORDER_NOTIONAL:.2f} order cap can't be enforced. Pass a limit_price "
            f"or check the symbol."
        )
    notional = est_price * float(qty)
    if notional > MAX_ORDER_NOTIONAL:
        return (
            f"REJECTED: estimated notional ${notional:.2f} exceeds cap "
            f"${MAX_ORDER_NOTIONAL:.2f}. Reduce qty to <= "
            f"{MAX_ORDER_NOTIONAL / est_price:.6f}."
        )

    side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
    tif = TimeInForce.GTC if _is_crypto(symbol) else TimeInForce.DAY

    if order_type == "limit":
        if not limit_price:
            return "REJECTED: limit order requires limit_price."
        req = LimitOrderRequest(
            symbol=symbol, qty=qty, side=side_enum,
            time_in_force=tif, limit_price=limit_price,
        )
    else:
        req = MarketOrderRequest(
            symbol=symbol, qty=qty, side=side_enum, time_in_force=tif,
        )

    o = trading.submit_order(req)
    return (
        f"OK [PAPER] order {o.id}\n"
        f"  {o.side} {o.qty} {o.symbol} ({o.order_type}) — status {o.status}\n"
        f"  est notional: ${notional:.2f} (cap ${MAX_ORDER_NOTIONAL:.2f})"
    )


@mcp.tool()
def get_orders(status: str = "open") -> str:
    """List orders. status: 'open', 'closed', or 'all'."""
    from alpaca.trading.requests import GetOrdersRequest
    from alpaca.trading.enums import QueryOrderStatus

    status_map = {
        "open": QueryOrderStatus.OPEN,
        "closed": QueryOrderStatus.CLOSED,
        "all": QueryOrderStatus.ALL,
    }
    req = GetOrdersRequest(status=status_map.get(status, QueryOrderStatus.OPEN), limit=50)
    orders = trading.get_orders(req)
    if not orders:
        return f"No {status} orders."
    return "\n".join(
        f"{o.id} | {o.side} {o.qty} {o.symbol} ({o.order_type}) — {o.status}"
        for o in orders
    )


@mcp.tool()
def cancel_order(order_id: str) -> str:
    """Cancel an open order by id."""
    trading.cancel_order_by_id(order_id)
    return f"Cancel requested for order {order_id}."


if __name__ == "__main__":
    mcp.run()
