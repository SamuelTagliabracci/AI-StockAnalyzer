import { useQuery } from '@tanstack/react-query'
import { fetchStocks, fetchCandles } from './api'

// Watchlist + latest quant analysis. Polls so the terminal stays live.
export function useStocks() {
  return useQuery({
    queryKey: ['stocks'],
    queryFn: fetchStocks,
    refetchInterval: 60_000,
  })
}

// Candles for the selected symbol only (chart is single-symbol).
export function useCandles(symbol: string | undefined) {
  return useQuery({
    queryKey: ['candles', symbol],
    queryFn: () => fetchCandles(symbol as string),
    enabled: Boolean(symbol),
    staleTime: 60_000,
  })
}
