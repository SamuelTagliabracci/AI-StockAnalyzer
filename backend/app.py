"""
AI Stock Market — backend API.

Lifted out of reference/AI-StockAnalyzer and made real:
  - serves the shared data pool (prices + quant analysis) over a small JSON API
  - the frontend terminal (web/) reads exclusively from here — no mock data

Fixes over the reference version (R1):
  1. None/NaN-guarding: every numeric field is coerced JSON-safe (NaN/inf -> null)
     so a single bad row no longer 500s the whole /api/stocks response.
  2. Price/target resolution: the displayed price is the latest close, and upside is
     recomputed against that live price (not the stale price captured at analysis time),
     so Current/Target/upside are internally consistent.
Plus: /api/candles/<symbol> for the chart, and currency tagging per symbol.
"""

import json
import logging
import math
import os
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

from database_manager import DatabaseManager
from data_ingestion_manager import DataIngestionManager
from stock_analyzer import StockAnalyzer
from market_sentiment import fetch_fear_greed
from trading.engine import execute_order, value_portfolio

# CNN Fear & Greed updates a few times an hour at most; cache live fetches in-process.
_FG_TTL = 600  # seconds
_fg_cache: dict = {"at": 0.0, "payload": None}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("MARKET_DB", os.path.join(os.path.dirname(__file__), "data", "market.db"))

# Canadian exchange suffixes (yfinance) → CAD; everything else we treat as USD.
# This is only a FALLBACK now — currency/exchange are tagged per-symbol at ingest
# time from yfinance (companies.currency / companies.exchange). See R2.
_CAD_SUFFIXES = (".TO", ".V", ".CN", ".NE")

# yfinance exchange codes → human labels for the terminal.
_EXCHANGE_LABELS = {
    "NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ", "NaN": "NASDAQ",
    "NYQ": "NYSE", "PCX": "NYSE Arca", "ASE": "NYSE American",
    "TOR": "TSX", "VAN": "TSXV", "CNQ": "CSE", "NEO": "NEO",
}


def currency_for(symbol: str) -> str:
    return "CAD" if symbol.upper().endswith(_CAD_SUFFIXES) else "USD"


def exchange_label(code, symbol: str) -> str:
    """Friendly exchange name from a yfinance code, falling back to a suffix guess.

    `code` may arrive as NaN (a float) when it comes from a pandas-read NULL column,
    so only trust a non-empty string.
    """
    if isinstance(code, str) and code:
        return _EXCHANGE_LABELS.get(code, code)
    return "TSX" if symbol.upper().endswith(_CAD_SUFFIXES) else "US"


def safe_float(x):
    """Return a finite float or None — keeps JSON valid (NaN/inf are not valid JSON)."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def safe_int(x):
    v = safe_float(x)
    return int(v) if v is not None else None


def confidence_for(total_score, risk_score) -> float:
    """Heuristic confidence from the quant scores (0..1). Honest stand-in until LLM agents (R3)."""
    total = total_score or 0
    risk = risk_score or 0
    c = 0.45 + 0.40 * (total / 100.0) - 0.15 * (risk / 100.0)
    return round(max(0.30, min(0.97, c)), 2)


def build_rationale(rec, total, fund, tech, mom, risk, price, target, upside) -> str:
    parts = [
        f"{rec}: composite {total}/100 "
        f"(fundamental {fund}/40, technical {tech}/30, momentum {mom}/30), risk {risk}/100."
    ]
    if price and target:
        parts.append(f"Target {price:.2f} → {target:.2f} ({upside:+.1f}%).")
    return " ".join(parts)


class MarketApp:
    def __init__(self, db_path: str = DB_PATH):
        self.db = DatabaseManager(db_path)
        self.ingestion = DataIngestionManager(self.db)
        self.analyzer = StockAnalyzer(self.db)
        self.progress = {"active": False}

        self.app = Flask(__name__)
        CORS(self.app)
        self._routes()
        logger.info("MarketApp ready (db=%s)", db_path)

    # ---- payload builders -------------------------------------------------

    def _price_snapshot(self, symbol):
        """Latest price/change plus volume and relative-volume from ~21 days of closes.

        rel_volume = latest volume ÷ avg of the prior 20 days — >1.5 flags 'unusual'
        activity, which the watchlist uses for its Volume/Trending sorts. One query.
        """
        df = self.db.get_price_data(symbol, days=21)
        if df is None or df.empty:
            return {"price": None, "change_pct": None, "volume": None, "rel_volume": None}
        price = safe_float(df.iloc[-1]["close"])
        change_pct = None
        if len(df) > 1:
            prev = safe_float(df.iloc[-2]["close"])
            if price is not None and prev:
                change_pct = round((price - prev) / prev * 100, 2)
        volume = safe_float(df.iloc[-1].get("volume"))
        rel_volume = None
        if len(df) > 1 and volume:
            prior = [safe_float(v) for v in df.iloc[:-1]["volume"].tolist()]
            prior = [v for v in prior if v]
            if prior:
                avg = sum(prior) / len(prior)
                if avg:
                    rel_volume = round(volume / avg, 2)
        return {"price": price, "change_pct": change_pct, "volume": volume, "rel_volume": rel_volume}

    @staticmethod
    def _upside(current, target) -> float:
        return round((target - current) / current * 100, 1) if (current and target) else 0.0

    def _holding_currency(self, symbol: str):
        """(None, currency) for a symbol — currency from company info, suffix as fallback."""
        comp = self.db.get_company(symbol) or {}
        currency = comp.get("currency") or (
            "CAD" if symbol.upper().endswith((".TO", ".V", ".CN", ".NE")) else "USD")
        return None, currency

    def _agent_verdict_payload(self, row: dict, current) -> dict:
        """Map a stored agent_verdicts row to the AICall shape the frontend renders.

        LLM/agent verdicts have no quant sub-scores, so those are null — the panel
        hides the score breakdown for non-quant agents.
        """
        target = safe_float(row.get("target_price"))
        return {
            "action": row.get("action") or "HOLD",
            "confidence": safe_float(row.get("confidence")) or 0.0,
            "totalScore": None,
            "fundamentalScore": None,
            "technicalScore": None,
            "momentumScore": None,
            "riskScore": None,
            "currentPrice": current,
            "targetPrice": target,
            "upsidePct": self._upside(current, target),
            "agent": row.get("agent") or "Agent",
            "horizon": row.get("horizon"),
            "rationale": row.get("rationale") or "",
        }

    def _stock_payload(self, analysis: dict, agent_verdicts: list | None = None) -> dict:
        symbol = analysis["symbol"]
        snap = self._price_snapshot(symbol)
        price, change_pct = snap["price"], snap["change_pct"]

        total = safe_int(analysis.get("total_score")) or 0
        fund = safe_int(analysis.get("fundamental_score")) or 0
        tech = safe_int(analysis.get("technical_score")) or 0
        mom = safe_int(analysis.get("momentum_score")) or 0
        risk = safe_int(analysis.get("risk_score")) or 0
        target = safe_float(analysis.get("target_price"))
        rec = analysis.get("recommendation") or "HOLD"

        # Price/target resolution fix: upside is measured against the *live* price.
        current = price if price is not None else safe_float(analysis.get("current_price"))
        if current and target:
            upside = round((target - current) / current * 100, 1)
        else:
            upside = round((safe_float(analysis.get("upside_potential")) or 0) * 100, 1)

        quant = {
            "action": rec,
            "confidence": confidence_for(total, risk),
            "totalScore": total,
            "fundamentalScore": fund,
            "technicalScore": tech,
            "momentumScore": mom,
            "riskScore": risk,
            "currentPrice": current,
            "targetPrice": target,
            "upsidePct": upside,
            "agent": "Quant Engine",
            "horizon": None,
            "rationale": build_rationale(rec, total, fund, tech, mom, risk, current, target, upside),
        }

        # verdicts[] is the multi-agent ledger; quant first, then any stored agents.
        verdicts = [quant] + [self._agent_verdict_payload(v, current) for v in (agent_verdicts or [])]

        return {
            "symbol": symbol,
            "name": analysis.get("name") or symbol,
            "sector": analysis.get("sector") or "Unknown",
            "currency": (analysis.get("currency") if isinstance(analysis.get("currency"), str) else None) or currency_for(symbol),
            "exchange": exchange_label(analysis.get("exchange"), symbol),
            "price": current,
            "changePct": change_pct if change_pct is not None else 0.0,
            "volume": snap["volume"],
            "relVolume": snap["rel_volume"],   # latest vs 20d avg; >1.5 ≈ unusual
            "call": quant,        # back-compat: the default/primary verdict
            "verdicts": verdicts,
        }

    # ---- routes -----------------------------------------------------------

    def _routes(self):
        app = self.app

        @app.route("/api/health")
        def health():
            return jsonify({"ok": True, "db": os.path.basename(DB_PATH), "stats": self.db.get_database_stats()})

        @app.route("/api/stocks")
        def stocks():
            try:
                analyses = self.db.get_all_latest_analyses()
                verdicts_by_symbol = self.db.get_all_latest_agent_verdicts()  # one query for all
                payload = []
                for a in analyses:
                    try:
                        payload.append(self._stock_payload(a, verdicts_by_symbol.get(a["symbol"])))
                    except Exception as e:  # one bad symbol must not sink the list
                        logger.error("Skipping %s in /api/stocks: %s", a.get("symbol"), e)
                payload.sort(key=lambda s: s["call"]["totalScore"], reverse=True)
                return jsonify({"stocks": payload, "total": len(payload)})
            except Exception as e:
                logger.error("Error in /api/stocks: %s", e)
                return jsonify({"error": str(e)}), 500

        @app.route("/api/candles/<symbol>")
        def candles(symbol):
            try:
                days = request.args.get("days", default=180, type=int)
                df = self.db.get_price_data(symbol, days=days)
                if df is None or df.empty:
                    return jsonify({"symbol": symbol, "candles": []})
                out = []
                for _, row in df.iterrows():
                    o, h, l, c = (safe_float(row[k]) for k in ("open", "high", "low", "close"))
                    if None in (o, h, l, c):
                        continue
                    out.append({
                        "time": str(row["date"])[:10],
                        "open": o, "high": h, "low": l, "close": c,
                        "volume": safe_int(row.get("volume")) or 0,
                    })
                return jsonify({"symbol": symbol, "candles": out})
            except Exception as e:
                logger.error("Error in /api/candles/%s: %s", symbol, e)
                return jsonify({"error": str(e)}), 500

        @app.route("/api/stocks/<symbol>/refresh", methods=["POST"])
        def refresh(symbol):
            """Pull fresh prices/fundamentals for one symbol, then re-run the quant analysis."""
            try:
                self.ingestion.update_company_data(symbol)
                analysis = self.analyzer.analyze_stock(symbol)
                if not analysis:
                    return jsonify({"success": False, "message": f"No data for {symbol}"}), 400
                row = self.db.get_latest_analysis(symbol) or {"symbol": symbol}
                comp = self.db.get_company(symbol) or {}
                row = {**row, "name": comp.get("name"), "sector": comp.get("sector"),
                       "currency": comp.get("currency"), "exchange": comp.get("exchange")}
                verdicts = self.db.get_all_latest_agent_verdicts().get(symbol)
                return jsonify({"success": True, "stock": self._stock_payload(row, verdicts)})
            except Exception as e:
                logger.error("Error refreshing %s: %s", symbol, e)
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/api/news/<symbol>")
        def news(symbol):
            """Recent news + announcements for one symbol (Yahoo Finance, 10-min cached)."""
            try:
                limit = request.args.get("limit", default=20, type=int)
                items = self.ingestion.get_company_news(symbol, limit=limit)
                return jsonify({"symbol": symbol, "news": items, "total": len(items)})
            except Exception as e:
                logger.error("Error in /api/news/%s: %s", symbol, e)
                return jsonify({"symbol": symbol, "news": [], "error": str(e)})

        @app.route("/api/accounts")
        def accounts():
            """All trading accounts with a quick valuation (for the AI Traders leaderboard)."""
            try:
                out = []
                for a in self.db.list_accounts():
                    v = value_portfolio(self.db, a["id"])
                    out.append({
                        "id": a["id"], "type": a["type"], "displayName": a["display_name"],
                        "email": a.get("email"), "agentKey": a.get("agent_key"),
                        "totalUsdEquiv": v["totalUsdEquiv"], "unrealizedPnl": v["unrealizedPnl"],
                        "unrealizedPnlPct": v["unrealizedPnlPct"], "positions": len(v["positions"]),
                    })
                return jsonify({"accounts": out})
            except Exception as e:
                logger.error("Error in /api/accounts: %s", e)
                return jsonify({"error": str(e)}), 500

        @app.route("/api/accounts/<int:account_id>/portfolio")
        def portfolio(account_id):
            try:
                acct = self.db.get_account(account_id)
                if not acct:
                    return jsonify({"error": "no such account"}), 404
                v = value_portfolio(self.db, account_id)
                v["account"] = {"id": acct["id"], "type": acct["type"],
                                "displayName": acct["display_name"], "agentKey": acct.get("agent_key")}
                return jsonify(v)
            except Exception as e:
                logger.error("Error in /api/accounts/%s/portfolio: %s", account_id, e)
                return jsonify({"error": str(e)}), 500

        @app.route("/api/accounts/<int:account_id>/trades")
        def account_trades(account_id):
            try:
                limit = request.args.get("limit", default=100, type=int)
                rows = self.db.get_trades(account_id, limit=limit)
                return jsonify({"trades": [{
                    "symbol": r["symbol"], "side": r["side"], "shares": safe_float(r["shares"]),
                    "price": safe_float(r["price"]), "currency": r.get("currency"),
                    "kind": r.get("kind"), "rationale": r.get("rationale"),
                    "createdAt": str(r.get("created_at")),
                } for r in rows]})
            except Exception as e:
                logger.error("Error in /api/accounts/%s/trades: %s", account_id, e)
                return jsonify({"error": str(e)}), 500

        @app.route("/api/accounts/<int:account_id>/orders", methods=["POST"])
        def place_order(account_id):
            """Manual order for a human account (paper). Body: {symbol, side, shares}."""
            try:
                body = request.get_json(force=True) or {}
                res = execute_order(self.db, account_id, body.get("symbol", ""),
                                    body.get("side", ""), body.get("shares", 0),
                                    kind="paper", rationale="manual")
                return jsonify(res), (200 if res.get("ok") else 400)
            except Exception as e:
                logger.error("Error in place_order %s: %s", account_id, e)
                return jsonify({"ok": False, "message": str(e)}), 500

        @app.route("/api/accounts/<int:account_id>/cash", methods=["POST"])
        def set_cash(account_id):
            """Manual cash entry. Body: {currency, amount} (absolute set)."""
            try:
                body = request.get_json(force=True) or {}
                ok = self.db.set_cash(account_id, body["currency"].upper(), float(body["amount"]))
                return jsonify({"ok": ok, "cash": self.db.get_cash(account_id)})
            except Exception as e:
                logger.error("Error set_cash %s: %s", account_id, e)
                return jsonify({"ok": False, "message": str(e)}), 400

        @app.route("/api/accounts/<int:account_id>/holdings", methods=["POST"])
        def set_holding(account_id):
            """Manually set an existing position (no cash impact). Body: {symbol, shares, avgCost}."""
            try:
                body = request.get_json(force=True) or {}
                symbol = body["symbol"].upper()
                _, currency = self._holding_currency(symbol)
                ok = self.db.upsert_holding(account_id, symbol, float(body["shares"]),
                                            float(body.get("avgCost") or 0), currency)
                return jsonify({"ok": ok})
            except Exception as e:
                logger.error("Error set_holding %s: %s", account_id, e)
                return jsonify({"ok": False, "message": str(e)}), 400

        @app.route("/api/signals")
        def signals():
            """Smart-money feed: recent disclosed trades by insiders/institutions/etc.

            Query params: ?symbol=AAPL (repeatable), ?source=insider, ?limit=200.
            """
            try:
                syms = request.args.getlist("symbol") or None
                source = request.args.get("source") or None
                limit = request.args.get("limit", default=200, type=int)
                rows = self.db.get_market_signals(symbols=syms, source=source, limit=limit)
                return jsonify({"signals": [self._signal_payload(r) for r in rows],
                                "total": len(rows)})
            except Exception as e:
                logger.error("Error in /api/signals: %s", e)
                return jsonify({"error": str(e)}), 500

        @app.route("/api/fear-greed")
        def fear_greed():
            """CNN Fear & Greed Index (market-wide sentiment, 0-100) + sub-indicators.

            Live fetch is cached in-process for 10 min; the last good reading is also
            persisted to system_settings so we can still serve a value if CNN is down.
            """
            now = time.monotonic()
            if _fg_cache["payload"] and now - _fg_cache["at"] < _FG_TTL:
                return jsonify({**_fg_cache["payload"], "stale": False})
            try:
                payload = fetch_fear_greed()
                _fg_cache.update(at=now, payload=payload)
                self.db.set_system_setting("fear_greed", json.dumps(payload))
                return jsonify({**payload, "stale": False})
            except Exception as e:
                logger.error("Error in /api/fear-greed: %s", e)
                cached = self.db.get_system_setting("fear_greed")
                if cached:
                    return jsonify({**json.loads(cached), "stale": True})
                return jsonify({"error": str(e)}), 502

    def _signal_payload(self, r: dict) -> dict:
        """Map a market_signals row to the camelCase shape the frontend feed renders."""
        return {
            "source": r.get("source"),
            "symbol": r.get("symbol"),
            "actor": r.get("actor"),
            "actorRole": r.get("actor_role"),
            "action": r.get("action"),
            "shares": safe_float(r.get("shares")),
            "valueUsd": safe_float(r.get("value_usd")),
            "price": safe_float(r.get("price")),
            "tradedAt": r.get("traded_at"),
            "filedAt": r.get("filed_at"),
            "url": r.get("url"),
        }

    def run(self, host="0.0.0.0", port=5000, debug=False):
        logger.info("Serving on http://%s:%s", host, port)
        self.app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    MarketApp().run(debug=bool(os.environ.get("FLASK_DEBUG")))
