# AI·TERMINAL — web frontend

Premium trading-terminal UI for the AI stock platform. **Vite + React + TS + Tailwind v4**,
TradingView `lightweight-charts`, Framer Motion. Multi-theme via a swappable token engine.

## Run
```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check + production build
```
The dev server proxies `/api` → `http://localhost:5000` (the Flask AI-StockAnalyzer backend).

## Themes
Three swappable skins on one layout (top-right switcher, or `?theme=<id>` deep link):
- `nasdaq` — flagship pro trading desk (polished)
- `fallout` — Vault-Tec / Pip-Boy CRT (green phosphor + scanlines)
- `empire` — Galactic Empire holo-console

A theme is just a map of CSS variables in `src/themes/themes.ts` + optional CSS flourishes
keyed on `[data-theme=...]` in `index.css`. Add a new theme by adding one entry.

## Structure
- `src/themes/` — theme tokens + provider (`applyTheme`, `useTheme`)
- `src/data/` — `types.ts` mirrors the backend analyzer output; `mock.ts` is placeholder data
- `src/components/` — Header, TickerTape, Watchlist, PriceChart, ScoreBar, AICallPanel, ThemeSwitcher

## Wiring to the backend (next)
Replace `src/data/mock.ts` with TanStack Query hooks hitting the Flask API:
- `GET /api/stocks` → watchlist + latest analysis (maps to `Stock[]`)
- `GET /api/stocks/<symbol>` → candles + fundamentals + the AI call
The `Stock` / `AICall` types already match `analysis_results` fields, so it's a thin adapter.
