import clsx from 'clsx'
import { usePortfolio, useTrades } from '../data/hooks'
import { fmt, pct, money, compact, timeAgo } from '../util'

// Renders any account's holdings + recent trades. Reused by AI Traders and My Portfolio.
export function AccountPortfolio({ accountId, onSelectSymbol }: { accountId: number; onSelectSymbol?: (s: string) => void }) {
  const { data: pf, isLoading } = usePortfolio(accountId)
  const { data: trades } = useTrades(accountId)

  if (isLoading || !pf) return <div className="dim text-[12px] p-6">Loading portfolio…</div>
  const pnlUp = pf.unrealizedPnl >= 0

  return (
    <div className="flex flex-col gap-3 p-3">
      {/* Summary tiles */}
      <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
        <Tile label="Total value (USD eq.)" value={`$${fmt(pf.totalUsdEquiv)}`} bright />
        <Tile label="Unrealized P&L" value={`${pnlUp ? '+' : ''}${fmt(pf.unrealizedPnl)}`} sub={pct(pf.unrealizedPnlPct)} cls={pnlUp ? 'up' : 'down'} />
        {Object.entries(pf.cash).map(([cur, amt]) => (
          <Tile key={cur} label={`Cash ${cur}`} value={fmt(amt)} />
        ))}
      </div>

      {/* Positions */}
      <section className="panel overflow-hidden">
        <div className="px-3 py-2 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
          <span className="tag">Positions</span>
          <span className="tag">{pf.positions.length}</span>
        </div>
        {pf.positions.length === 0 ? (
          <div className="dim text-[11px] p-4 text-center">No open positions.</div>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="dim text-[10px] uppercase tracking-wider">
                <th className="text-left font-normal px-3 py-1.5">Symbol</th>
                <th className="text-right font-normal px-3 py-1.5">Shares</th>
                <th className="text-right font-normal px-3 py-1.5">Avg</th>
                <th className="text-right font-normal px-3 py-1.5">Price</th>
                <th className="text-right font-normal px-3 py-1.5">Value</th>
                <th className="text-right font-normal px-3 py-1.5">P&L</th>
              </tr>
            </thead>
            <tbody>
              {pf.positions.map((p) => {
                const up = p.unrealizedPnl >= 0
                return (
                  <tr
                    key={p.symbol}
                    className={clsx('border-b', onSelectSymbol && 'row-hover cursor-pointer')}
                    style={{ borderColor: 'var(--border)' }}
                    onClick={onSelectSymbol ? () => onSelectSymbol(p.symbol) : undefined}
                  >
                    <td className="mono text-[12px] px-3 py-1.5" style={{ color: 'var(--text-bright)' }}>{p.symbol} <span className="dim text-[9px]">{p.currency}</span></td>
                    <td className="mono text-[12px] px-3 py-1.5 text-right">{fmt(p.shares, 2)}</td>
                    <td className="mono text-[11px] px-3 py-1.5 text-right dim">{fmt(p.avgCost)}</td>
                    <td className="mono text-[11px] px-3 py-1.5 text-right">{p.price != null ? fmt(p.price) : '—'}</td>
                    <td className="mono text-[12px] px-3 py-1.5 text-right" style={{ color: 'var(--text-bright)' }}>{fmt(p.marketValue)}</td>
                    <td className={clsx('mono text-[11px] px-3 py-1.5 text-right', up ? 'up' : 'down')}>{up ? '+' : ''}{fmt(p.unrealizedPnl)}<div className="text-[9px]">{pct(p.unrealizedPnlPct)}</div></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </section>

      {/* Trade history */}
      <section className="panel overflow-hidden">
        <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
          <span className="tag">Trade history</span>
        </div>
        {!trades || trades.length === 0 ? (
          <div className="dim text-[11px] p-4 text-center">No trades yet.</div>
        ) : (
          <div className="max-h-[240px] overflow-y-auto">
            {trades.map((t, i) => {
              const buy = t.side === 'BUY'
              return (
                <div key={i} className="px-3 py-1.5 border-b flex items-center gap-2 text-[11px]" style={{ borderColor: 'var(--border)' }}>
                  <span className={clsx('mono w-10', buy ? 'up' : 'down')}>{t.side}</span>
                  <span className="mono" style={{ color: 'var(--text-bright)' }}>{compact(t.shares)} {t.symbol}</span>
                  <span className="dim">@ {fmt(t.price)} {t.currency}</span>
                  {t.rationale && <span className="tag text-[8px]">{t.rationale}</span>}
                  <span className="dim ml-auto">{timeAgo(t.createdAt)}</span>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}

function Tile({ label, value, sub, cls, bright }: { label: string; value: string; sub?: string; cls?: string; bright?: boolean }) {
  return (
    <div className="rounded-md px-3 py-2" style={{ background: 'var(--panel-2)' }}>
      <div className="tag">{label}</div>
      <div className={clsx('mono text-[16px]', cls)} style={bright && !cls ? { color: 'var(--text-bright)' } : undefined}>{value}</div>
      {sub && <div className={clsx('mono text-[11px]', cls)}>{sub}</div>}
    </div>
  )
}
