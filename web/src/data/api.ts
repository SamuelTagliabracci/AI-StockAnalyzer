// Real data client. Talks to the Flask backend (proxied at /api in dev).
// The backend already returns the exact `Stock`/`AICall` shape, so no field remapping needed.
import type { Stock, Candle } from './types'

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} → ${res.status} ${res.statusText}`)
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
