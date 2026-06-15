# AI Stock Market — Product Roadmap

> Forward-looking plan. For system design + principles see [ARCHITECTURE.md](ARCHITECTURE.md).
> This file is the source of truth for *where we're going*; ARCHITECTURE.md is *how it's built*.

## The vision (end goals)

1. **Give great financial advice** — many AI agents independently analyze the same
   facts and each emit a clear, actionable call: recommendation (STRONG BUY … SELL),
   a price prediction, and a **trade plan** (e.g. "buy NVDA ≤ $220, target $260, stop $195,
   horizon 12M"). You click any stock and see what *every* agent thinks, side by side.
2. **Let agents actually trade** — each agent runs a (paper, then real) portfolio, places
   orders from its own recommendations, and we get **performance reports over 1D / 1W / 1M /
   3M / 6M / 1Y / 5Y / 10Y** so we can see — honestly, over time — which agents are good.
3. **Learn which agents are accurate** — every prediction is logged with price-at-time +
   horizon and scored against what actually happened. A leaderboard ranks agents by
   accuracy, P&L, and risk-adjusted return vs a buy-and-hold benchmark.

**The agent roster we want competing:**
Quant Engine · Claude Code · OpenAI (GPT) · Google Gemini · xAI Grok · DeepSeek ·
Ollama **Cloud** models · Ollama **local** models (RTX 5090) · later, custom **ML models**.

---

## Where we are today (2026-06-15)

**Done — Phase 1 (Foundation):**
- ✅ **R1** — Real backend (Flask + SQLite) + React terminal UI, real data only.
- ✅ **R2** — Multi-market universe (112 symbols: 47 US + 65 TSX), data-driven currency/exchange tags.
- ✅ **R3 slice 1** — Multi-agent verdict ledger (`agent_verdicts`), `/api/stocks` returns
  `verdicts[]`, `backend/agents/claude_analyst.py` (Claude Code = first real agent, no API key),
  10 starter Claude verdicts, agent-switcher in the UI. Each verdict already stores
  **price_at_call + horizon** → predictions are scoreable from day one.

**Done — since 2026-06-02 (build-out across Phases 2 & 3):**
- ✅ **R3 slice 2 — Ollama analyst** (`backend/agents/ollama_analyst.py`): second real agent
  (qwen/llama via `localhost:11434`), GPU now unblocked. Two live agents competing.
- ✅ **Stock Detail + Market views** (`StockDetail.tsx`, `MarketView.tsx`): click-through
  per-stock page with agent calls — partial Phase 2.2.
- ✅ **Paper trading engine** (`backend/trading/`: engine, seed, autonomous trader loop):
  per-agent accounts/cash/holdings/trades tables, `/api/accounts*` endpoints, autonomous
  AI trader ($10k, 3×/day). UI: `Portfolio.tsx`, `AccountPortfolio.tsx`, `AITraders.tsx`,
  `TradeTicket.tsx` — partial Phase 3.1.
- ✅ **Smart Money feed** (`backend/signals/`, `market_signals` table, `/api/signals`,
  `SmartMoney.tsx`): SEC Form 4 insider trades LIVE; congress/institution/copytrade stubbed.
- ✅ **Fear & Greed Index** (`backend/market_sentiment.py`, `/api/fear-greed`,
  `FearGreedGauge.tsx`): CNN market-wide sentiment gauge on the Market view.
- ✅ **Data backfill** (`backend/backfill.py`): all prices refreshed to 2026-06-11;
  MEG.TO delisted. (Resolved the stale-TSX-prices blocker below.)

**Known blockers / prerequisites:**
- ✅ ~~NVIDIA driver down~~ — resolved; GPU unblocked, Ollama serving the local tier.
- 🔑 **No API keys** for OpenAI / Gemini / Grok / DeepSeek → those tiers are stubbed until keys exist.
- ✅ ~~Legacy TSX prices stale~~ — resolved via `backfill.py` (fresh to 2026-06-11).

---

## Phase 2 — Many agents, comparison view, accuracy tracking

> This is the heart of the current request: a fleet of agents, a click-through comparison,
> and tracking who's right over time.

### 2.1 — Agent provider framework
Make adding an agent a config change, not a code rewrite.
- **Agent registry** (`agents` table or config): `id, name, provider, model, type
  (quant|llm|ml), enabled, cost_tier`. Drives the roster the UI shows.
- **Common agent interface**: `analyze(bundle) -> Verdict`. The bundle (quant scores +
  fundamentals + recent price action + later news/macro) is the *same* for every agent —
  differences reflect reasoning, not data access (the core principle).
- **Provider adapters**, one per backend, all behind the interface:
  - `claude_analyst.py` ✅ (done) — Claude Code, no key.
  - `ollama_agent.py` — talks to `localhost:11434`; works for **local** (RTX 5090, after
    driver fix) **and** Ollama **Cloud** models (same API, different host/key).
  - `openai_agent.py`, `gemini_agent.py`, `grok_agent.py`, `deepseek_agent.py` — gated on keys;
    stubbed (registry `enabled=false`) until keys exist.
  - `quant_engine` — wrap the existing analyzer as an agent so it lives in the same ledger.
- **Verdict-ingest API**: `POST /api/agents/<agent>/verdict` so any agent/process can write
  (lets us run agents out-of-process, on a schedule, or from other machines).
- **Structured trade plan** on every verdict — extend `agent_verdicts`:
  `entry_price` (buy at/below), `target_price` (sell), `stop_loss`, `horizon`, `thesis`/`strategy`
  text. This is the "buy NVDA at $X, sell at $Y" the user wants.

### 2.2 — Stock detail / comparison view
Click a stock → a full page (not just the side panel) that shows:
- **Agent comparison table**: row per agent — action (color-coded), confidence, entry/target/stop,
  implied upside, horizon, and a one-line thesis. Sort by confidence or action.
- **Consensus strip**: distribution of calls (e.g. "5 BUY / 2 HOLD / 1 SELL"), average target,
  spread/disagreement indicator.
- **Per-agent rationale** drill-down (expand a row to read the full reasoning).
- **Track-record badge per agent on this stock**: how their *past* calls on this symbol played out.
- Chart overlays: each agent's entry/target as horizontal markers on the candlestick chart.

### 2.3 — Prediction tracking & accuracy scoring
Turn the verdict log into a scoreboard.
- **Outcome evaluator** (scheduled job): for each verdict, at horizon checkpoints
  (and continuously), compare prediction vs actual price → store in a `verdict_outcomes` table:
  direction-correct?, return since call, error vs target, max favorable/adverse excursion.
- **Per-agent accuracy metrics**: hit rate (direction), avg return per call, target-hit rate,
  calibration (does 80% confidence ≈ 80% right?), Sharpe of the implied trades.
- **Leaderboard page**: rank agents across all stocks and per sector/market, filterable by
  horizon. Benchmark every agent vs buy-and-hold SPY / TSX.
- **Backtest the agents on history** (don't wait a year): replay agents over 2023–2025 price
  history to bootstrap track records immediately (the quant + ML agents can; LLM agents get
  scored going forward as they emit live calls).

**Phase 2 definition of done:** click any stock, see ≥4 agents' calls + trade plans side by side;
a leaderboard ranks them by measured accuracy; new agents added via registry + adapter.

---

## Phase 3 — Paper trading, then real trading, with performance reports

> "Actually have the agents perform trades based on their recommendations."

### 3.1 — Paper portfolios per agent
- Each agent has a simulated portfolio (starting cash, e.g. $100 or $100k for resolution).
- **Daily loop**: refresh data → each agent reasons → emits/updates verdicts → an execution
  layer turns verdicts into paper orders (respecting the agent's entry/target/stop plan) →
  fills at pooled prices → positions + cash updated → everything logged.
- Position sizing / risk rules per agent (e.g. max % per name, cash buffer).

### 3.2 — Performance reports
- Per-agent equity curve and returns over **1D / 1W / 1M / 3M / 6M / 1Y / 5Y / 10Y**
  (5Y/10Y via historical backtest until live time accrues).
- Metrics: total return, CAGR, max drawdown, Sharpe/Sortino, win rate, vs benchmark.
- Compare agents on one chart; drill into any agent's trade history.

### 3.3 — Human-in-the-loop + real execution (Canada)
- HITL approval queue: you approve an agent's pick → routed to (paper, then) real fills.
  Track "what-if" (auto) vs "approved" performance separately.
- Broker-agnostic execution interface; write a **Questrade** or **IBKR** adapter
  (Alpaca unavailable in Canada), or crypto via Kraken/NDAX. Fund ~$100 to start.

**Phase 3 definition of done:** every agent has a tracked paper portfolio with multi-horizon
reports; a real broker adapter exists behind a HITL approval gate.

---

## Phase 4 — Custom ML price/outcome models

> "Real machine learning … train models on years and years of history … predict prices
> and outcomes." These become first-class **ML agents** in the same arena.

- **Data**: we have years of OHLCV + fundamentals per symbol → build a feature store
  (technical indicators, fundamental ratios, lagged returns, regime/macro features).
- **Targets**: forward N-day return, direction, probability of hitting target before stop,
  volatility. Frame as regression + classification.
- **Models**: start classic (gradient-boosted trees / XGBoost-style) for tabular features;
  progress to sequence models (LSTM/Temporal-CNN/Transformer) on price+volume; the RTX 5090
  is the training box once the driver's fixed.
- **Rigor**: walk-forward / time-series cross-validation (no lookahead), out-of-sample test
  windows, compare vs the LLM agents and the buy-and-hold benchmark on the *same* leaderboard.
- **Serve** trained models as agents via the same `analyze(bundle) -> Verdict` interface, so
  ML predictions show up in the comparison view and get scored like everyone else.

**Phase 4 definition of done:** ≥1 trained ML model competing in the arena, scored head-to-head
against LLM + quant agents with honest out-of-sample validation.

---

## Immediate next steps (when you're back)

1. **Fix the NVIDIA driver** → `ollama serve` + pull a model (e.g. `llama3.1`, `qwen2.5`) →
   wire `ollama_agent.py` as the second real agent (local tier). *(In progress.)*
2. **Build the agent registry + verdict-ingest endpoint** (Phase 2.1) — small, unblocks every
   later agent and lets agents run out-of-process.
3. **Stock detail comparison view** (Phase 2.2) — the "click a stock, see all agents" screen.
4. **Outcome evaluator + leaderboard** (Phase 2.3) — start scoring who's right.
5. Add **entry/stop/strategy** fields to verdicts so calls are real trade plans.
6. (Anytime) batch-refresh stale TSX prices; add API keys as they become available.

## Backlog / nice-to-haves
- News (RSS) + SEC 13F + congressional-trade feeds into the shared pool (followed-trader "agents").
- Macro (BoC/Fed) context in the analyst bundle.
- Skin polish (Fallout CRT/boot anim, Empire r3f starfield).
- Multi-user: humans compete alongside AIs; copy-trading.
