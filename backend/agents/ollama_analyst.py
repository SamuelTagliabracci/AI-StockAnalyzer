"""Ollama local-model analysts — the self-hosted tier (R3, tier 2).

Each local model (qwen2.5:7b, llama3.1:8b, ...) reads the same analyst *bundle* the
Claude analyst reads, reasons over it, and writes a verdict to the agent_verdicts
ledger. Because every tier shares bundle() + write_verdict(), local and premium models
are scored head-to-head later (R5). Runs against `ollama serve` on localhost:11434 —
no API key, all on the RTX 5060 (8 GB VRAM, so ~7-8B quantized models).

Usage:
    python -m agents.ollama_analyst run qwen2.5:7b NVDA AAPL RY.TO   # analyze + persist
    python -m agents.ollama_analyst run llama3.1:8b NVDA --dry       # print, don't write
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_manager import DatabaseManager
from agents.claude_analyst import bundle, DB_PATH

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# Human-facing agent label per model id; falls back to the raw model id if unlisted.
_AGENT_LABELS = {
    "qwen2.5:7b": "Qwen2.5 7B",
    "llama3.1:8b": "Llama 3.1 8B",
}

_VALID_ACTIONS = {"STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"}
_VALID_HORIZONS = {"1M", "3M", "6M", "12M", "24M"}

_SYSTEM = (
    "You are a disciplined equity analyst. You are given a JSON bundle for one stock: "
    "quant scores, fundamentals, recent price action, and (if present) market_sentiment — "
    "the CNN Fear & Greed index (0=extreme fear, 100=extreme greed). Weigh them and issue a "
    "single verdict. Let stock-specific evidence dominate, but tilt conviction with the market "
    "mood: be more cautious when the market is greedy, more opportunistic when it is fearful. "
    "Be decisive but honest about uncertainty. Respond with ONLY a JSON object, "
    "no prose, matching exactly this schema:\n"
    '{"action": one of ["STRONG BUY","BUY","HOLD","SELL","STRONG SELL"], '
    '"confidence": number 0.0-1.0, '
    '"target_price": number (your 12-month price target, same currency as last_close), '
    '"horizon": one of ["1M","3M","6M","12M","24M"], '
    '"rationale": string (2-4 sentences citing the specific numbers that drove the call)}'
)


def _post(path: str, payload: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        OLLAMA_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def analyze(db: DatabaseManager, model: str, symbol: str) -> dict:
    """Send one symbol's bundle to a local model and return its parsed verdict.

    Raises ValueError if the model's output can't be coerced into a valid verdict.
    """
    data = bundle(db, symbol)
    resp = _post("/api/chat", {
        "model": model,
        "format": "json",          # constrain Ollama to emit valid JSON
        "stream": False,
        "options": {"temperature": 0.3},
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": json.dumps(data, default=str)},
        ],
    })
    content = (resp.get("message") or {}).get("content", "")
    try:
        v = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"{model} returned non-JSON for {symbol}: {content[:200]}") from e

    action = str(v.get("action", "")).replace("_", " ").upper().strip()
    if action not in _VALID_ACTIONS:
        raise ValueError(f"{model} gave invalid action {action!r} for {symbol}")
    horizon = str(v.get("horizon", "12M")).upper().strip()
    if horizon not in _VALID_HORIZONS:
        horizon = "12M"
    try:
        confidence = max(0.0, min(1.0, float(v.get("confidence"))))
    except (TypeError, ValueError):
        confidence = 0.5
    try:
        target_price = float(v["target_price"])
    except (TypeError, ValueError, KeyError):
        target_price = None

    return {
        "symbol": symbol,
        "action": action,
        "confidence": confidence,
        "target_price": target_price,
        "horizon": horizon,
        "rationale": str(v.get("rationale", "")).strip(),
    }


def _write_verdict(db: DatabaseManager, agent: str, model: str, v: dict) -> bool:
    """Persist a local-model verdict, stamping price_at_call for later scoring (R5)."""
    prices = db.get_price_data(v["symbol"], days=2)
    price_at_call = float(prices["close"].iloc[-1]) if (prices is not None and not prices.empty) else None
    return db.add_agent_verdict({
        "agent": agent,
        "model": model,
        "symbol": v["symbol"],
        "action": v["action"],
        "confidence": v["confidence"],
        "target_price": v["target_price"],
        "price_at_call": price_at_call,
        "horizon": v["horizon"],
        "rationale": v["rationale"],
    })


def run(db: DatabaseManager, model: str, symbols: list, dry: bool = False) -> int:
    """Analyze each symbol with `model`; persist verdicts unless dry. Returns # written."""
    agent = _AGENT_LABELS.get(model, model)
    written = 0
    for sym in symbols:
        try:
            v = analyze(db, model, sym)
        except (ValueError, urllib.error.URLError, OSError) as e:
            print(f"  ! {sym}: {e}", file=sys.stderr)
            continue
        line = f"  {sym:<8} {v['action']:<11} conf={v['confidence']:.2f} " \
               f"target={v['target_price']} {v['horizon']}"
        if dry:
            print(line + "  (dry)")
            print(f"      {v['rationale']}")
            continue
        if _write_verdict(db, agent, model, v):
            written += 1
            print(line + "  ✓")
        else:
            print(line + "  FAILED", file=sys.stderr)
    return written


def _main(argv):
    if len(argv) >= 3 and argv[0] == "run":
        dry = "--dry" in argv
        model = argv[1]
        symbols = [a for a in argv[2:] if not a.startswith("--")]
        db = DatabaseManager(DB_PATH)
        n = run(db, model, symbols, dry=dry)
        if not dry:
            print(f"wrote {n} verdict(s) as {_AGENT_LABELS.get(model, model)}")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    _main(sys.argv[1:])
