// Mirrors the AI-StockAnalyzer backend output so wiring to the Flask API later is trivial.

export type Action =
  | 'STRONG BUY'
  | 'BUY'
  | 'MODERATE BUY'
  | 'HOLD'
  | 'WEAK HOLD'
  | 'CONSIDER SELLING'
  | 'SELL'

export interface Candle {
  time: string // 'YYYY-MM-DD'
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface AICall {
  action: Action
  confidence: number // 0..1
  // Quant sub-scores — present only for the Quant Engine; null for LLM agents.
  totalScore: number | null // 0..100
  fundamentalScore: number | null
  technicalScore: number | null
  momentumScore: number | null
  riskScore: number | null // 0..100 (higher = riskier)
  currentPrice: number
  targetPrice: number
  upsidePct: number
  // Which "agent" produced this call (Quant Engine, Claude Code, an Ollama model, …)
  agent: string
  horizon?: string | null // e.g. '12M' — the prediction window (LLM agents)
  rationale: string
}

export interface Stock {
  symbol: string
  name: string
  sector: string
  currency: string
  exchange: string // e.g. 'NASDAQ', 'NYSE', 'TSX'
  price: number
  changePct: number
  // Candles are fetched per-symbol on demand (see useCandles), not bundled in the list.
  candles?: Candle[]
  call: AICall // the default/primary verdict (Quant Engine) — kept for back-compat
  // The multi-agent ledger: every agent's latest verdict for this stock.
  verdicts?: AICall[]
}
