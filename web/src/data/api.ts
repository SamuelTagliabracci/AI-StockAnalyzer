// Real data client. Talks to the Flask backend (proxied at /api in dev).
// The backend already returns the exact `Stock`/`AICall` shape, so no field remapping needed.
import type { Stock, Candle, Signal, SignalSource, NewsItem, Account, Portfolio, Trade, FearGreed } from './types'

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} → ${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return res.json() as Promise<T>
}

export async function fetchStocks(): Promise<Stock[]> {
  const data = await getJSON<{ stocks: Stock[] }>('/api/stocks')
  return data.stocks
}

export async function fetchCandles(symbol: string, days = 180): Promise<Candle[]> {
  const data = await getJSON<{ candles: Candle[] }>(
    `/api/candles/${encodeURIComponent(symbol)}?days=${days}`,
  )
  return data.candles
}

// --- Phase 3: trading ---
export async function fetchAccounts(): Promise<Account[]> {
  const data = await getJSON<{ accounts: Account[] }>('/api/accounts')
  return data.accounts
}

export async function fetchPortfolio(id: number): Promise<Portfolio> {
  return getJSON<Portfolio>(`/api/accounts/${id}/portfolio`)
}

export async function fetchTrades(id: number): Promise<Trade[]> {
  const data = await getJSON<{ trades: Trade[] }>(`/api/accounts/${id}/trades`)
  return data.trades
}

export async function placeOrder(
  id: number, order: { symbol: string; side: string; shares: number },
): Promise<{ ok: boolean; message: string }> {
  return postJSON(`/api/accounts/${id}/orders`, order)
}

export async function setCash(id: number, currency: string, amount: number) {
  return postJSON<{ ok: boolean }>(`/api/accounts/${id}/cash`, { currency, amount })
}

export async function setHolding(id: number, symbol: string, shares: number, avgCost: number) {
  return postJSON<{ ok: boolean }>(`/api/accounts/${id}/holdings`, { symbol, shares, avgCost })
}

export async function fetchNews(symbol: string, limit = 20): Promise<NewsItem[]> {
  const data = await getJSON<{ news: NewsItem[] }>(
    `/api/news/${encodeURIComponent(symbol)}?limit=${limit}`,
  )
  return data.news
}

export async function fetchFearGreed(): Promise<FearGreed> {
  return getJSON<FearGreed>('/api/fear-greed')
}

export async function fetchSignals(
  opts: { symbol?: string; source?: SignalSource; limit?: number } = {},
): Promise<Signal[]> {
  const q = new URLSearchParams()
  if (opts.symbol) q.set('symbol', opts.symbol)
  if (opts.source) q.set('source', opts.source)
  q.set('limit', String(opts.limit ?? 200))
  const data = await getJSON<{ signals: Signal[] }>(`/api/signals?${q}`)
  return data.signals
}
