import type { Stock } from '../data/types'
import { fmt, pct, actionColor } from '../util'
import clsx from 'clsx'

interface Props {
  stocks: Stock[]
  selected: string
  onSelect: (symbol: string) => void
}

export function Watchlist({ stocks, selected, onSelect }: Props) {
  return (
    <aside className="panel panel-glow flex flex-col w-[240px] shrink-0 overflow-hidden">
      <div className="px-3 py-2 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
        <span className="tag">Watchlist</span>
        <span className="tag">{stocks.length}</span>
      </div>
      <div className="overflow-y-auto flex-1">
        {stocks.map((s) => {
          const up = s.changePct >= 0
          return (
            <button
              key={s.symbol}
              onClick={() => onSelect(s.symbol)}
              className={clsx('row-hover w-full text-left px-3 py-2 border-b flex items-center justify-between gap-2', selected === s.symbol && 'row-active')}
              style={{ borderColor: 'var(--border)' }}
            >
              <div className="min-w-0">
                <div className="mono text-[13px]" style={{ color: 'var(--text-bright)' }}>{s.symbol}</div>
                <div className="text-[10px] truncate dim">{s.name}</div>
              </div>
              <div className="text-right shrink-0">
                <div className="mono text-[12px]">{fmt(s.price)}</div>
                <div className={clsx('mono text-[11px]', up ? 'up' : 'down')}>{up ? '▲' : '▼'} {pct(s.changePct)}</div>
              </div>
              <div className="w-1.5 self-stretch rounded-full" style={{ background: actionColor(s.call.action), opacity: 0.8 }} />
            </button>
          )
        })}
      </div>
    </aside>
  )
}
