import { useMemo, useState } from 'react'
import clsx from 'clsx'
import type { Stock } from '../data/types'
import { fmt, pct, compact, actionColor } from '../util'
import { useFearGreed } from '../data/hooks'
import { FearGreedGauge } from './FearGreedGauge'

interface Props {
  stocks: Stock[]
  onSelectSymbol: (symbol: string) => void
}

// Exchange scopes. 'ALL' aggregates everything; the rest filter by Stock.exchange.
type Scope = 'ALL' | 'NASDAQ' | 'NYSE' | 'TSX'
const SCOPES: Scope[] = ['ALL', 'NASDAQ', 'NYSE', 'TSX']

// Each leaderboard = a label + how to rank + the per-row metric to show on the right.
interface Board {
  key: string
  label: string
  rank: (a: Stock, b: Stock) => number
  metric: (s: Stock) => string
  // Only include rows where the metric is meaningful.
  keep?: (s: Stock) => boolean
}

const BOARDS: Board[] = [
  {
    key: 'gainers',
    label: '🚀 Top Gainers',
    rank: (a, b) => b.changePct - a.changePct,
    metric: (s) => pct(s.changePct),
  },
  {
    key: 'losers',
    label: '📉 Top Losers',
    rank: (a, b) => a.changePct - b.changePct,
    metric: (s) => pct(s.changePct),
  },
  {
    key: 'active',
    label: '🔊 Most Active',
    rank: (a, b) => (b.volume ?? 0) - (a.volume ?? 0),
    metric: (s) => compact(s.volume ?? null),
    keep: (s) => (s.volume ?? 0) > 0,
  },
  {
    key: 'trending',
    label: '🔥 Trending',
    rank: (a, b) => (b.relVolume ?? 0) - (a.relVolume ?? 0),
    metric: (s) => `${fmt(s.relVolume ?? 0, 1)}×`,
    keep: (s) => (s.relVolume ?? 0) > 0,
  },
  {
    key: 'rated',
    label: '⭐ Top Rated',
    rank: (a, b) => (b.call.totalScore ?? 0) - (a.call.totalScore ?? 0),
    metric: (s) => `${s.call.totalScore ?? 0}`,
  },
]

const TOP_N = 8

export function MarketView({ stocks, onSelectSymbol }: Props) {
  const [scope, setScope] = useState<Scope>('ALL')
  const [query, setQuery] = useState('')
  const fearGreed = useFearGreed()

  const scoped = useMemo(
    () => (scope === 'ALL' ? stocks : stocks.filter((s) => s.exchange === scope)),
    [stocks, scope],
  )

  // Search runs across the WHOLE market (ignores the exchange scope) so you can always
  // find any holding. Non-empty query replaces the leaderboards with a results list.
  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return null
    return stocks
      .filter((s) => s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q))
      .sort((a, b) => (b.call.totalScore ?? 0) - (a.call.totalScore ?? 0))
  }, [stocks, query])

  // Market breadth for the current scope.
  const breadth = useMemo(() => {
    let adv = 0, dec = 0, flat = 0, sumChg = 0, vol = 0
    for (const s of scoped) {
      if (s.changePct > 0) adv++
      else if (s.changePct < 0) dec++
      else flat++
      sumChg += s.changePct
      vol += s.volume ?? 0
    }
    return {
      adv, dec, flat, vol,
      avg: scoped.length ? sumChg / scoped.length : 0,
    }
  }, [scoped])

  return (
    <main className="panel panel-glow flex-1 flex flex-col min-w-0 overflow-hidden">
      {/* Header: title + exchange scope tabs */}
      <div className="px-4 py-3 border-b flex items-center justify-between flex-wrap gap-3" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3">
          <h1 className="mono font-bold text-[20px] tracking-wide" style={{ color: 'var(--text-bright)' }}>
            MARKET
          </h1>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search any ticker or name…"
            className="mono text-[12px] px-2 py-1.5 rounded outline-none w-[220px]"
            style={{ background: 'var(--panel-2)', border: '1px solid var(--border-bright)', color: 'var(--text-bright)' }}
          />
        </div>
        <div className={clsx('flex items-center gap-1.5 flex-wrap', query && 'opacity-40 pointer-events-none')}>
          {SCOPES.map((sc) => {
            const count = sc === 'ALL' ? stocks.length : stocks.filter((s) => s.exchange === sc).length
            return (
              <button key={sc} onClick={() => setScope(sc)} className={clsx('btn', scope === sc && 'btn-active')}>
                {sc === 'ALL' ? 'All' : sc} <span className="opacity-60">{count}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Breadth strip */}
      <div className="px-4 py-2 border-b flex items-center gap-5 flex-wrap text-[12px]" style={{ borderColor: 'var(--border)' }}>
        <Breadth label="Advancing" value={breadth.adv} cls="up" />
        <Breadth label="Declining" value={breadth.dec} cls="down" />
        <Breadth label="Unchanged" value={breadth.flat} />
        <div className="flex items-center gap-1.5">
          <span className="dim">Avg</span>
          <span className={clsx('mono', breadth.avg >= 0 ? 'up' : 'down')}>{pct(breadth.avg)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="dim">Volume</span>
          <span className="mono" style={{ color: 'var(--text-bright)' }}>{compact(breadth.vol)}</span>
        </div>
      </div>

      {/* Market-wide sentiment: CNN Fear & Greed Index. */}
      <FearGreedGauge data={fearGreed.data} loading={fearGreed.isLoading} />

      {/* Search results replace the leaderboards while typing. */}
      {results ? (
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="px-4 py-2 dim text-[11px] border-b" style={{ borderColor: 'var(--border)' }}>
            {results.length} match{results.length === 1 ? '' : 'es'} for “{query}”
          </div>
          {results.map((s) => {
            const up = s.changePct >= 0
            return (
              <button
                key={s.symbol}
                onClick={() => onSelectSymbol(s.symbol)}
                className="row-hover w-full text-left px-4 py-2 border-b flex items-center gap-3"
                style={{ borderColor: 'var(--border)' }}
              >
                <span className="mono text-[13px]" style={{ color: 'var(--text-bright)' }}>{s.symbol}</span>
                <span className="tag text-[8px] px-1 py-0">{s.exchange}</span>
                <span className="dim text-[11px] flex-1 truncate">{s.name}</span>
                <span className="mono text-[12px]">{fmt(s.price)}</span>
                <span className={clsx('mono text-[11px] w-16 text-right', up ? 'up' : 'down')}>{up ? '▲' : '▼'} {pct(s.changePct)}</span>
              </button>
            )
          })}
          {results.length === 0 && <div className="dim text-[12px] p-6 text-center">No stocks match “{query}”.</div>}
        </div>
      ) : (
      /* Leaderboard grid */
      <div className="flex-1 min-h-0 overflow-y-auto p-3">
        <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
          {BOARDS.map((board) => {
            const rows = [...scoped]
              .filter(board.keep ?? (() => true))
              .sort(board.rank)
              .slice(0, TOP_N)
            return (
              <section key={board.key} className="panel flex flex-col overflow-hidden">
                <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
                  <span className="mono text-[13px]" style={{ color: 'var(--text-bright)' }}>{board.label}</span>
                </div>
                <div>
                  {rows.length === 0 && <div className="dim text-[11px] p-3 text-center">No data.</div>}
                  {rows.map((s, i) => {
                    const up = s.changePct >= 0
                    return (
                      <button
                        key={s.symbol}
                        onClick={() => onSelectSymbol(s.symbol)}
                        className="row-hover w-full text-left px-3 py-1.5 border-b flex items-center gap-2"
                        style={{ borderColor: 'var(--border)' }}
                      >
                        <span className="dim mono text-[10px] w-4 shrink-0">{i + 1}</span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="mono text-[12px]" style={{ color: 'var(--text-bright)' }}>{s.symbol}</span>
                            <span className="tag text-[8px] px-1 py-0 shrink-0" title={`${s.exchange} · ${s.currency}`}>{s.exchange}</span>
                          </div>
                          <div className="dim text-[10px] truncate">{s.name}</div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="mono text-[11px]">{fmt(s.price)}</div>
                          <div className={clsx('mono text-[10px]', up ? 'up' : 'down')}>{up ? '▲' : '▼'} {pct(s.changePct)}</div>
                        </div>
                        <div className="mono text-[11px] w-16 text-right shrink-0" style={{ color: 'var(--accent)' }}>
                          {board.metric(s)}
                        </div>
                        <div className="w-1 self-stretch rounded-full" style={{ background: actionColor(s.call.action), opacity: 0.8 }} />
                      </button>
                    )
                  })}
                </div>
              </section>
            )
          })}
        </div>
      </div>
      )}
    </main>
  )
}

function Breadth({ label, value, cls }: { label: string; value: number; cls?: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="dim">{label}</span>
      <span className={clsx('mono', cls)} style={!cls ? { color: 'var(--text-bright)' } : undefined}>{value}</span>
    </div>
  )
}
