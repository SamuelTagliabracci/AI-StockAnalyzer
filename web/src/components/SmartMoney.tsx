import { useState } from 'react'
import clsx from 'clsx'
import type { SignalSource } from '../data/types'
import { useSignals } from '../data/hooks'
import { money, compact } from '../util'

interface Props {
  // When set, the feed is scoped to one symbol; null shows the whole market.
  symbol: string | null
  onClearSymbol: () => void
}

// Source pills. Insider is live; the rest are wired but awaiting a data source.
const SOURCES: { key: SignalSource | 'all'; label: string; live: boolean }[] = [
  { key: 'all', label: 'All', live: true },
  { key: 'insider', label: 'Insiders', live: true },
  { key: 'institution', label: '13F Funds', live: false },
  { key: 'congress', label: 'Congress', live: false },
  { key: 'copytrade', label: 'Copy Traders', live: false },
]

const SOURCE_TAG: Record<SignalSource, string> = {
  insider: 'INSIDER',
  institution: '13F',
  congress: 'CONGRESS',
  copytrade: 'COPY',
}

export function SmartMoney({ symbol, onClearSymbol }: Props) {
  const [source, setSource] = useState<SignalSource | 'all'>('all')
  const { data: signals, isLoading, isError, error } = useSignals({
    symbol: symbol ?? undefined,
    source: source === 'all' ? undefined : source,
  })

  return (
    <main className="panel panel-glow flex-1 flex flex-col min-w-0 overflow-hidden">
      <div className="px-4 py-3 border-b flex items-center justify-between flex-wrap gap-3" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-baseline gap-3">
          <h1 className="mono font-bold text-[20px] tracking-wide" style={{ color: 'var(--text-bright)' }}>
            SMART MONEY
          </h1>
          <span className="dim text-[12px]">disclosed trades by the big players</span>
          {symbol && (
            <button onClick={onClearSymbol} className="tag" title="Show the whole market">
              {symbol} ✕
            </button>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {SOURCES.map((s) => (
            <button
              key={s.key}
              onClick={() => setSource(s.key)}
              className={clsx('tag', source === s.key && 'row-active')}
              title={s.live ? 'Live data' : 'Wired — awaiting a data source'}
            >
              {s.label}
              {!s.live && <span className="dim"> ·stub</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Coverage caveat — be honest about what the feed can and can't see. */}
      <div className="px-4 py-1.5 border-b dim text-[10px] leading-relaxed" style={{ borderColor: 'var(--border)' }}>
        Live: US insider trades (SEC Form 4, ~2-day lag). 13F / Congress / Copy-trade are wired but
        await a data source. Canadian (.TO) names are sparse — insiders file with SEDI, not the SEC.
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        {isLoading && <Center>Loading feed…</Center>}
        {isError && <Center>Feed error: {(error as Error)?.message}</Center>}
        {signals && signals.length === 0 && (
          <Center>No disclosed trades{symbol ? ` for ${symbol}` : ''} in this view yet.</Center>
        )}
        {signals && signals.length > 0 && (
          <table className="w-full border-collapse">
            <thead>
              <tr className="dim text-[10px] uppercase tracking-wider sticky top-0" style={{ background: 'var(--panel)' }}>
                <th className="text-left font-normal px-3 py-1.5">Filed</th>
                <th className="text-left font-normal px-3 py-1.5">Symbol</th>
                <th className="text-left font-normal px-3 py-1.5">Who</th>
                <th className="text-left font-normal px-3 py-1.5">Action</th>
                <th className="text-right font-normal px-3 py-1.5">Shares</th>
                <th className="text-right font-normal px-3 py-1.5">Value</th>
                <th className="text-right font-normal px-3 py-1.5">Price</th>
                <th className="px-3 py-1.5" />
              </tr>
            </thead>
            <tbody>
              {signals.map((s, i) => {
                const buy = s.action === 'BUY'
                return (
                  <tr key={i} className="row-hover border-b" style={{ borderColor: 'var(--border)' }}>
                    <td className="mono text-[11px] px-3 py-1.5 dim whitespace-nowrap">{s.filedAt ?? '—'}</td>
                    <td className="mono text-[12px] px-3 py-1.5" style={{ color: 'var(--text-bright)' }}>{s.symbol}</td>
                    <td className="px-3 py-1.5">
                      <div className="text-[12px]">{s.actor ?? '—'}</div>
                      <div className="dim text-[10px] flex items-center gap-1.5">
                        <span className="tag text-[8px] px-1 py-0">{SOURCE_TAG[s.source]}</span>
                        {s.actorRole}
                      </div>
                    </td>
                    <td className={clsx('mono text-[12px] px-3 py-1.5', buy ? 'up' : 'down')}>
                      {buy ? '▲ BUY' : '▼ SELL'}
                    </td>
                    <td className="mono text-[12px] px-3 py-1.5 text-right">{compact(s.shares)}</td>
                    <td className="mono text-[12px] px-3 py-1.5 text-right" style={{ color: 'var(--text-bright)' }}>{money(s.valueUsd)}</td>
                    <td className="mono text-[11px] px-3 py-1.5 text-right dim">{s.price != null ? s.price.toFixed(2) : '—'}</td>
                    <td className="px-3 py-1.5 text-right">
                      {s.url && (
                        <a href={s.url} target="_blank" rel="noreferrer" className="tag" title="Open the SEC filing">↗</a>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </main>
  )
}

function Center({ children }: { children: React.ReactNode }) {
  return <div className="h-full flex items-center justify-center dim text-[12px] p-6 text-center">{children}</div>
}
