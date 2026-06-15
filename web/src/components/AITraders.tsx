import { useMemo, useState } from 'react'
import clsx from 'clsx'
import { useAccounts } from '../data/hooks'
import { fmt, pct } from '../util'
import { AccountPortfolio } from './AccountPortfolio'

// The arena: every AI agent's autonomous $10k paper book, ranked. Pick one to drill in.
export function AITraders({ onSelectSymbol }: { onSelectSymbol?: (s: string) => void }) {
  const { data: accounts, isLoading } = useAccounts()
  const [picked, setPicked] = useState<number | null>(null)

  const agents = useMemo(
    () => (accounts ?? []).filter((a) => a.type === 'agent').sort((a, b) => b.totalUsdEquiv - a.totalUsdEquiv),
    [accounts],
  )
  const selected = picked ?? agents[0]?.id ?? null

  return (
    <main className="panel panel-glow flex-1 flex flex-col min-w-0 overflow-hidden">
      <div className="px-4 py-3 border-b flex items-center gap-3" style={{ borderColor: 'var(--border)' }}>
        <h1 className="mono font-bold text-[20px] tracking-wide" style={{ color: 'var(--text-bright)' }}>AI TRADERS</h1>
        <span className="dim text-[12px]">autonomous agents · $10k each · they trade themselves, no approval · re-analyze 3×/day</span>
      </div>

      {isLoading ? (
        <div className="dim text-[12px] p-6">Loading agents…</div>
      ) : (
        <div className="flex-1 min-h-0 flex">
          {/* Leaderboard */}
          <div className="w-[280px] shrink-0 border-r overflow-y-auto" style={{ borderColor: 'var(--border)' }}>
            {agents.map((a, i) => {
              const up = a.unrealizedPnl >= 0
              return (
                <button
                  key={a.id}
                  onClick={() => setPicked(a.id)}
                  className={clsx('row-hover w-full text-left px-3 py-3 border-b flex items-center gap-3', selected === a.id && 'row-active')}
                  style={{ borderColor: 'var(--border)' }}
                >
                  <span className="mono text-[16px] dim w-5">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="mono text-[13px]" style={{ color: 'var(--text-bright)' }}>{a.displayName}</div>
                    <div className="dim text-[10px]">{a.positions} position{a.positions === 1 ? '' : 's'}</div>
                  </div>
                  <div className="text-right">
                    <div className="mono text-[13px]" style={{ color: 'var(--text-bright)' }}>${fmt(a.totalUsdEquiv)}</div>
                    <div className={clsx('mono text-[10px]', up ? 'up' : 'down')}>{up ? '+' : ''}{fmt(a.unrealizedPnl)} ({pct(a.unrealizedPnlPct)})</div>
                  </div>
                </button>
              )
            })}
          </div>

          {/* Selected agent's book */}
          <div className="flex-1 min-w-0 overflow-y-auto">
            {selected != null && <AccountPortfolio accountId={selected} onSelectSymbol={onSelectSymbol} />}
          </div>
        </div>
      )}
    </main>
  )
}
