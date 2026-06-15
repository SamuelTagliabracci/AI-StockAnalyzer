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

// --- Phase 3: trading accounts -------------------------------------------------
export interface Account {
  id: number
  type: 'human' | 'agent'
  displayName: string
  email: string | null
  agentKey: string | null
  totalUsdEquiv: number
  unrealizedPnl: number
  unrealizedPnlPct: number
  positions: number
}

export interface Position {
  symbol: string
  shares: number
  avgCost: number
  price: number | null
  currency: string
  marketValue: number
  costBasis: number
  unrealizedPnl: number
  unrealizedPnlPct: number
}

export interface Portfolio {
  account: { id: number; type: string; displayName: string; agentKey: string | null }
  cash: Record<string, number>
  positions: Position[]
  byCurrency: Record<string, { cash: number; positions: number; total: number }>
  totalUsdEquiv: number
  unrealizedPnl: number
  unrealizedPnlPct: number
}

export interface Trade {
  symbol: string
  side: string
  shares: number
  price: number
  currency: string | null
  kind: string | null
  rationale: string | null
  createdAt: string
}

// A news article or company announcement for a symbol (Yahoo Finance).
export interface NewsItem {
  id: string | null
  title: string | null
  summary: string | null
  publisher: string | null
  published_at: string | null // ISO timestamp
  url: string | null
  thumbnail: string | null
  kind: string // 'story' | 'video' | 'announcement' | …
}

// One disclosed "smart money" trade in the feed (SEC Form 4 insider, 13F, Congress, …).
export type SignalSource = 'insider' | 'institution' | 'congress' | 'copytrade'

export interface Signal {
  source: SignalSource
  symbol: string
  actor: string | null // who traded (insider name, fund, politician)
  actorRole: string | null // e.g. 'Director', 'CEO', '10% Owner'
  action: 'BUY' | 'SELL'
  shares: number | null
  valueUsd: number | null
  price: number | null
  tradedAt: string | null // when the trade happened (YYYY-MM-DD)
  filedAt: string | null // when it became public
  url: string | null // source filing
}

// CNN Fear & Greed Index — market-wide sentiment gauge (0 = extreme fear, 100 = extreme greed).
export interface FearGreedComponent {
  key: string
  label: string
  score: number | null
  rating: string | null
}

export interface FearGreed {
  score: number | null
  rating: string | null // 'extreme fear' | 'fear' | 'neutral' | 'greed' | 'extreme greed'
  timestamp: string | null
  previousClose: number | null
  previous1Week: number | null
  previous1Month: number | null
  previous1Year: number | null
  components: FearGreedComponent[]
  history: number[] // trailing daily scores, oldest → newest (for the sparkline)
  stale?: boolean // true if served from cache because the live fetch failed
}

export interface Stock {
  symbol: string
  name: string
  sector: string
  currency: string
  exchange: string // e.g. 'NASDAQ', 'NYSE', 'TSX'
  price: number
  changePct: number
  volume?: number | null
  relVolume?: number | null // latest volume ÷ 20-day avg; >1.5 ≈ unusual activity
  // Candles are fetched per-symbol on demand (see useCandles), not bundled in the list.
  candles?: Candle[]
  call: AICall // the default/primary verdict (Quant Engine) — kept for back-compat
  // The multi-agent ledger: every agent's latest verdict for this stock.
  verdicts?: AICall[]
}
