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
  totalScore: number // 0..100
  fundamentalScore: number
  technicalScore: number
  momentumScore: number
  riskScore: number // 0..100 (higher = riskier)
  currentPrice: number
  targetPrice: number
  upsidePct: number
  // Which "agent" produced this call (Claude, a local Ollama model, etc.)
  agent: string
  rationale: string
}

export interface Stock {
  symbol: string
  name: string
  sector: string
  currency: string
  price: number
  changePct: number
  // Candles are fetched per-symbol on demand (see useCandles), not bundled in the list.
  candles?: Candle[]
  call: AICall
}
