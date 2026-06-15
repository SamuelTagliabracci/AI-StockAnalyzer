import type { Action } from './data/types'

export const cssVar = (name: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim()

export function actionColor(action: Action): string {
  if (action.includes('BUY')) return 'var(--up)'
  if (action.includes('SELL') || action === 'CONSIDER SELLING') return 'var(--down)'
  return 'var(--warn)'
}

export const fmt = (n: number, d = 2) =>
  n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })

export const pct = (n: number) => `${n >= 0 ? '+' : ''}${fmt(n, 2)}%`

// Compact USD for the feed: 88_148_400 → '$88.1M', 1_500 → '$1.5K'.
export function money(n: number | null): string {
  if (n == null) return '—'
  const abs = Math.abs(n)
  if (abs >= 1e9) return `$${fmt(n / 1e9, 1)}B`
  if (abs >= 1e6) return `$${fmt(n / 1e6, 1)}M`
  if (abs >= 1e3) return `$${fmt(n / 1e3, 1)}K`
  return `$${fmt(n, 0)}`
}

// Relative time for news: '3h ago', '2d ago'. Falls back to the raw date on parse fail.
export function timeAgo(iso: string | null): string {
  if (!iso) return ''
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return iso
  const s = Math.floor((Date.now() - t) / 1000)
  if (s < 60) return 'just now'
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  if (d < 30) return `${d}d ago`
  return new Date(t).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// Compact share count: 400_000 → '400K', 1_250_000 → '1.25M'.
export function compact(n: number | null): string {
  if (n == null) return '—'
  const abs = Math.abs(n)
  if (abs >= 1e6) return `${fmt(n / 1e6, 2)}M`
  if (abs >= 1e3) return `${fmt(n / 1e3, 0)}K`
  return fmt(n, 0)
}
