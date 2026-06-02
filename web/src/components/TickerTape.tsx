import type { Stock } from '../data/types'
import { fmt, pct } from '../util'

export function TickerTape({ stocks }: { stocks: Stock[] }) {
  // Duplicate the list so the -50% translate loop is seamless.
  const items = [...stocks, ...stocks]
  return (
    <div className="panel panel-glow overflow-hidden h-9 flex items-center shrink-0">
      <div className="px-3 h-full flex items-center border-r mono text-[11px] tracking-widest shrink-0"
           style={{ borderColor: 'var(--border)', color: 'var(--text-bright)' }}>
        <span className="live-dot mr-2" /> LIVE
      </div>
      <div className="ticker-track">
        {items.map((s, i) => {
          const up = s.changePct >= 0
          return (
            <span key={i} className="mono text-[12px] inline-flex items-center gap-2">
              <span style={{ color: 'var(--text-bright)' }}>{s.symbol}</span>
              <span className="dim">{fmt(s.price)}</span>
              <span className={up ? 'up' : 'down'}>
                {up ? '▲' : '▼'} {pct(s.changePct)}
              </span>
            </span>
          )
        })}
      </div>
    </div>
  )
}
