import { useQuery } from '@tanstack/react-query'
import { fetchStocks, fetchCandles, fetchSignals, fetchNews, fetchAccounts, fetchPortfolio, fetchTrades, fetchFearGreed } from './api'
import type { SignalSource } from './types'

// Watchlist + latest quant analysis. Polls so the terminal stays live.
export function useStocks() {
  return useQuery({
    queryKey: ['stocks'],
    queryFn: fetchStocks,
    refetchInterval: 60_000,
  })
}

// Candles for the selected symbol only (chart is single-symbol). `days` drives the
// detail view's range selector (1M/6M/1Y/MAX).
export function useCandles(symbol: string | undefined, days = 180) {
  return useQuery({
    queryKey: ['candles', symbol, days],
    queryFn: () => fetchCandles(symbol as string, days),
    enabled: Boolean(symbol),
    staleTime: 60_000,
  })
}

// News + announcements for the symbol shown in the detail view.
export function useNews(symbol: string | undefined) {
  return useQuery({
    queryKey: ['news', symbol],
    queryFn: () => fetchNews(symbol as string),
    enabled: Boolean(symbol),
    staleTime: 300_000, // backend caches 10 min; no need to refetch aggressively
  })
}

// --- Phase 3: trading accounts ---
export function useAccounts() {
  return useQuery({ queryKey: ['accounts'], queryFn: fetchAccounts, refetchInterval: 30_000 })
}

export function usePortfolio(id: number | undefined) {
  return useQuery({
    queryKey: ['portfolio', id],
    queryFn: () => fetchPortfolio(id as number),
    enabled: Boolean(id),
    refetchInterval: 30_000,
  })
}

export function useTrades(id: number | undefined) {
  return useQuery({
    queryKey: ['trades', id],
    queryFn: () => fetchTrades(id as number),
    enabled: Boolean(id),
    refetchInterval: 30_000,
  })
}

// CNN Fear & Greed Index — market-wide sentiment. Backend caches 10 min.
export function useFearGreed() {
  return useQuery({
    queryKey: ['fear-greed'],
    queryFn: fetchFearGreed,
    refetchInterval: 600_000,
    staleTime: 300_000,
  })
}

// Smart-money feed: disclosed insider/institutional/etc. trades, optionally filtered.
export function useSignals(opts: { symbol?: string; source?: SignalSource } = {}) {
  return useQuery({
    queryKey: ['signals', opts.symbol ?? 'all', opts.source ?? 'all'],
    queryFn: () => fetchSignals(opts),
    refetchInterval: 120_000,
  })
}
