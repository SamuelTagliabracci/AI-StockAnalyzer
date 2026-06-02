# AI Stock Market — Architecture

**Goal:** Give an AI ~$100 (eventually) and let it analyze markets, recommend, and
trade — long-hold and active. This year is **paper + backtest validation**: prove the
system has edge before real money. Multiple AIs (and humans) compete as tracked
"agents," all reading the same scraped facts. Real execution is a later toggle.

Constraints we are designing around (as of 2026-05-29):
- **No paid API keys** (no OpenAI, no Anthropic API key). → Claude Code itself is the
  premium analyst, run on a schedule. Local models on an RTX 5090 via Ollama + Ollama
  Cloud are the competing agents. DeepSeek/OpenAI/etc. are stubbed until keys exist.
- **No brokerage account yet.** → Everything is simulated. Real execution plugs in
  later via `../alpaca-mcp` (Alpaca, free to open).

## Principle: scrape once, share with every agent
A single **data pool** fetches prices, news, filings, and disclosures *once per cycle*.
Every agent reads identical facts, so performance differences reflect *reasoning*, not
data access. No agent hits external APIs directly.

## Components
```
SHARED DATA POOL  → prices (yfinance) · news (RSS) · SEC 13F (EDGAR) · congress trades
      │             (free, no keys)
AGENTS            → Claude(scheduled) · Ollama-local · Ollama-cloud · human(you) ·
      │             followed-trader feeds (Pelosi/13F) · external-AI stubs (DeepSeek…)
SIMULATED LEDGER  → each agent has a paper portfolio; orders fill at pooled prices
PREDICTIONS LOG   → every recommendation stored w/ price-at-time + horizon + confidence
VALIDATION        → score predictions vs outcomes; backtest on history; leaderboard
HITL QUEUE        → you approve picks → (later) routed to alpaca-mcp for real fills
```

## Cherry-picked from the cloned repos (`reference/`)
- **TradingAgents** — multi-agent reasoning (analyst roles → debate → decision). Output
  is recommendations only, which is exactly what feeds our ledger.
- **LLM-TradeBot** — risk management, portfolio accounting, reflection patterns.
- **AI-Trader** — multi-user, leaderboard, signal-feed, copy-trading concepts.

## Free data sources (no keys)
- **Prices / OHLCV / history:** `yfinance` (years of history → enables immediate backtest)
- **News:** public RSS (Yahoo Finance, Reuters, etc.)
- **Institutional/famous holdings:** SEC EDGAR 13F filings (public)
- **Congressional trades (Pelosi et al.):** house/senate stock-watcher public datasets

## Validation philosophy
We do **not** wait a year. Backtest the recommendation strategy on 2023–2025 history
first; only run forward paper trading once a strategy shows edge. Every prediction is
scored (direction accuracy, P&L, Sharpe, vs buy-and-hold SPY benchmark) so agents can
self-improve and we can compare them honestly over a long horizon.

## Roadmap

### Done (2026-05-29)
- ✅ Confirmed free data pipe: `yfinance` for TSX (`.TO`, CAD) + US, 2yr history, no keys.
- ✅ Foundation chosen: build on `reference/AI-StockAnalyzer` (data pool + quant analyzer + BoC macro + Flask API). Verified it runs end-to-end (2 known bugs).
- ✅ **Flagship web frontend built & running** (`web/`): Vite+React+TS+Tailwind v4, TradingView
  candlestick charts, Framer Motion, swappable **theme engine** with 3 working skins
  (NASDAQ Terminal flagship, Fallout/Pip-Boy, Galactic Empire). Mock data; types already
  mirror backend `analysis_results`.

### Done (2026-05-30)
- ✅ **R1 — Made it real.** `git init`. Lifted the analyzer out of `reference/` into a
  proper `backend/` package (`app.py` + the 4 modules) serving real data from
  `backend/data/market.db` (65 companies, 33k price rows, 130 analyses). Fixed the 2 bugs:
  None/NaN-guarding (JSON-safe `/api/stocks`, one bad row no longer 500s the list) and
  price/target resolution (upside recomputed vs the live close). Added `/api/candles/<symbol>`
  and currency tagging. Frontend now reads **only** real data via TanStack Query
  (`web/src/data/{api,hooks}.ts`); `mock.ts` deleted. Verified end-to-end through the Vite proxy.

### Done (2026-06-02)
- ✅ **R2 — Multi-market universe.** Universe expanded from TSX-only to **US + TSX**:
  `Config.US_SYMBOLS` (47 NASDAQ/NYSE large caps) + `Config.UNIVERSE = US_SYMBOLS + TSX_SYMBOLS`
  (112 symbols); ingestion iterates `UNIVERSE` (TSX-only naming retired). **Exchange/currency
  are now data-driven**, tagged per-symbol from yfinance at ingest (`companies.currency`/`exchange`)
  rather than guessed from the suffix — suffix logic remains only as a fallback. Added an
  idempotent migration (new columns + CAD backfill for legacy TSX rows). API payload carries
  `currency` + a friendly `exchange` label (NMS→NASDAQ, NYQ→NYSE, TOR→TSX); frontend `Stock`
  type + watchlist show the exchange chip. Ingested + analyzed all 47 US names (prices fresh
  through 2026-06-01); verified end-to-end: `/api/stocks` returns 65 CAD/TSX + 47 USD
  (19 NASDAQ / 28 NYSE). NOTE: legacy TSX **prices** are still stale (end 2025-09-03) and TSX
  `exchange` codes are unset (labelled "TSX" via fallback) until a full refresh is run.

- ✅ **R3 slice 1 — Multi-agent framework + Claude as the first real agent.** Added the
  `agent_verdicts` ledger (one row per agent×symbol: action, confidence, target, **price_at_call +
  horizon** → scoreable predictions for R5) with an idempotent migration. `/api/stocks` now returns
  `verdicts[]` per stock (Quant Engine first, then any agents); `call` kept as back-compat default.
  New `backend/agents/` package: `claude_analyst.py` builds the analyst input *bundle* (quant scores
  + fundamentals + recent returns) and writes verdicts — **Claude Code is the model, no API key
  needed**. Generated the first 10 real Claude verdicts (5 US + 5 TSX), deliberately diverging from
  the quant where warranted (e.g. trimming TD's unrealistic C$149 target to C$115, flagging SHOP's
  119× forward P/E). Frontend: `AICallPanel` gains an **agent switcher** (pills), hides the quant
  sub-score breakdown for LLM agents, and shows the horizon; defaults to Claude when present.
  Verified end-to-end through the Vite proxy.

### Next (priority order)
- **R3 slice 2 — More agent tiers:** Ollama Cloud + local RTX 5090 models (BLOCKED: NVIDIA driver
  down — `nvidia-smi` fails; fix needed before local models run on GPU), external (DeepSeek/OpenAI)
  stubbed until keys. Add a `POST` verdict-ingest endpoint so non-Claude agents can write. Make the
  Claude analyst run on a **schedule** rather than manually.
- **R4 — Paper ledger + daily analyst loop:** simulated portfolio per agent; daily cycle
  refresh→reason→execute→log predictions with price-at-time + horizon.
- **R5 — Validation / backtest + leaderboard:** backtest on existing price history (don't wait
  a year); score direction accuracy, P&L, Sharpe, drawdown vs SPY/TSX benchmark; rank agents.
- **R6 — Feeds & HITL:** news RSS + politician/13F (Pelosi etc.) feeds into the pool;
  human-in-the-loop approval queue (approve → would-be-real); track "what-if" simulated vs approved.
- **R7 — Multi-user + skin polish:** humans + AIs as tracked users, you-vs-AI paper trading,
  leaderboards, copy-trading. Polish Fallout (CRT shader/boot anim) + Empire (r3f starfield).
- **R8 — Real execution (Canada):** broker-agnostic execution interface; write **Questrade** or
  **IBKR** adapter (Alpaca unavailable in Canada), or crypto via Kraken/NDAX. Fund ~$100.
