import { useMemo, useState } from 'react'
import type { Stock } from '../data/types'
import { fmt, pct, actionColor, compact } from '../util'
import clsx from 'clsx'

interface Props {
  stocks: Stock[]
  selected: string
  onSelect: (symbol: string) => void
}

// "Where the action is" sorts. Each maps to a comparator over the stock list.
type SortKey = 'score' | 'gainers' | 'losers' | 'volume' | 'trending' | 'az'

const SORTS: { key: SortKey; label: string }[] = [
  { key: 'score', label: 'Score' },
  { key: 'gainers', label: 'Top Gainers' },
  { key: 'losers', label: 'Top Losers' },
  { key: 'volume', label: 'Top Volume' },
  { key: 'trending', label: 'Trending' }, // by relative volume (unusual activity)
  { key: 'az', label: 'A–Z' },
]

const comparator: Record<SortKey, (a: Stock, b: Stock) => number> = {
  score: (a, b) => (b.call.totalScore ?? 0) - (a.call.totalScore ?? 0),
  gainers: (a, b) => b.changePct - a.changePct,
  losers: (a, b) => a.changePct - b.changePct,
  volume: (a, b) => (b.volume ?? 0) - (a.volume ?? 0),
  trending: (a, b) => (b.relVolume ?? 0) - (a.relVolume ?? 0),
  az: (a, b) => a.symbol.localeCompare(b.symbol),
}

export function Watchlist({ stocks, selected, onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortKey>('score')

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    const filtered = q
      ? stocks.filter(
          (s) => s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q),
        )
      : stocks
    return [...filtered].sort(comparator[sort])
  }, [stocks, query, sort])

  return (
    <aside className="panel panel-glow flex flex-col w-[260px] shrink-0 overflow-hidden">
      <div className="px-3 py-2 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
        <span className="tag">Watchlist</span>
        <span className="tag">{rows.length}{query && ` / ${stocks.length}`}</span>
      </div>

      {/* Search — type a ticker or company name to find your stocks. */}
      <div className="px-2 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search ticker or name…"
          className="w-full mono text-[12px] px-2 py-1.5 rounded outline-none"
          style={{ background: 'var(--panel-2)', border: '1px solid var(--border-bright)', color: 'var(--text-bright)' }}
        />
        <div className="flex flex-wrap gap-1 mt-1.5">
          {SORTS.map((s) => (
            <button
              key={s.key}
              onClick={() => setSort(s.key)}
              className={clsx('tag', sort === s.key && 'row-active')}
              title={s.key === 'trending' ? 'Sort by unusual volume (vs 20-day average)' : undefined}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-y-auto flex-1">
        {rows.length === 0 && (
          <div className="dim text-[11px] p-4 text-center">No matches for “{query}”.</div>
        )}
        {rows.map((s) => {
          const up = s.changePct >= 0
          const hot = (s.relVolume ?? 0) >= 1.5 // unusual volume flag
          return (
            <button
              key={s.symbol}
              onClick={() => onSelect(s.symbol)}
              className={clsx('row-hover w-full text-left px-3 py-2 border-b flex items-center justify-between gap-2', selected === s.symbol && 'row-active')}
              style={{ borderColor: 'var(--border)' }}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="mono text-[13px]" style={{ color: 'var(--text-bright)' }}>{s.symbol}</span>
                  <span className="tag text-[8px] px-1 py-0 shrink-0" title={`${s.exchange} · ${s.currency}`}>{s.exchange}</span>
                  {hot && (
                    <span className="text-[9px] shrink-0" title={`Unusual volume: ${s.relVolume}× the 20-day average`}>🔥{s.relVolume}×</span>
                  )}
                </div>
                <div className="text-[10px] truncate dim">{s.name}</div>
              </div>
              <div className="text-right shrink-0">
                <div className="mono text-[12px]">{fmt(s.price)}</div>
                <div className={clsx('mono text-[11px]', up ? 'up' : 'down')}>{up ? '▲' : '▼'} {pct(s.changePct)}</div>
                {(sort === 'volume' || sort === 'trending') && s.volume != null && (
                  <div className="mono text-[9px] dim">vol {compact(s.volume)}</div>
                )}
              </div>
              <div className="w-1.5 self-stretch rounded-full" style={{ background: actionColor(s.call.action), opacity: 0.8 }} />
            </button>
          )
        })}
      </div>
    </aside>
  )
}
