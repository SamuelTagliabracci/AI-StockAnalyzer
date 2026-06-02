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
