# Reference repositories

Upstream projects cloned under `reference/` for design inspiration while building this
system. Each carries its own `.git`; they are **not** part of this repo (the `reference/`
directory is gitignored). This file just records where they came from.

For *how* each one informed the design, see the
"Cherry-picked from the cloned repos" section in [../ARCHITECTURE.md](../ARCHITECTURE.md).

| Folder | GitHub | Cloned at | What we took from it |
|--------|--------|-----------|----------------------|
| `reference/AI-StockAnalyzer` | https://github.com/SamuelTagliabracci/AI-StockAnalyzer | `d0756d5` | Our own original project — the foundation this system grew out of (data pool + quant analyzer + BoC macro + Flask API). |
| `reference/TradingAgents` | https://github.com/TauricResearch/TradingAgents | `61522e1` | Multi-agent reasoning (analyst roles → debate → decision); output is recommendations, which feed our verdict ledger. |
| `reference/LLM-TradeBot` | https://github.com/EthanAlgoX/LLM-TradeBot | `b443a5b` | Risk management, portfolio accounting, and reflection patterns. |
| `reference/AI-Trader` | https://github.com/HKUDS/AI-Trader | `dcdccb2` | Multi-user, leaderboard, signal-feed, and copy-trading concepts. |

> Note: `AI-StockAnalyzer`'s original code is also preserved on its GitHub repo under the
> `original-stockanalyzer` branch (this project now lives on `main`).
