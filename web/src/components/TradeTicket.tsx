import { useState } from 'react'
import clsx from 'clsx'
import { useQueryClient } from '@tanstack/react-query'
import type { Stock } from '../data/types'
import { useAccounts } from '../data/hooks'
import { placeOrder } from '../data/api'
import { fmt } from '../util'

type Side = 'BUY' | 'SELL'

// Your manual trade ticket — executes a paper order against your account (Phase 3 engine).
// You approve your own trades; the AI agents trade autonomously on their own books.
export function TradeTicket({ stock }: { stock: Stock }) {
  const { data: accounts } = useAccounts()
  const qc = useQueryClient()
  const human = (accounts ?? []).find((a) => a.type === 'human')

  const [side, setSide] = useState<Side>('BUY')
  const [qty, setQty] = useState('')
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  const shares = Number(qty) || 0
  const estimate = shares * stock.price

  async function submit() {
    if (shares <= 0) { setNote({ ok: false, text: 'Enter a share quantity first.' }); return }
    if (!human) { setNote({ ok: false, text: 'No account found — run the seed script.' }); return }
    setBusy(true)
    try {
      const res = await placeOrder(human.id, { symbol: stock.symbol, side, shares })
      setNote({ ok: res.ok, text: res.message })
      if (res.ok) {
        setQty('')
        qc.invalidateQueries({ queryKey: ['accounts'] })
        qc.invalidateQueries({ queryKey: ['portfolio', human.id] })
        qc.invalidateQueries({ queryKey: ['trades', human.id] })
      }
    } catch (e) {
      setNote({ ok: false, text: (e as Error).message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col">
      <div className="px-3 py-2 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
        <span className="tag">Trade</span>
        <span className="tag dim">{human ? human.displayName : 'your account'}</span>
      </div>

      <div className="p-3 flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-2">
          {(['BUY', 'SELL'] as Side[]).map((s) => (
            <button
              key={s}
              onClick={() => { setSide(s); setNote(null) }}
              className={clsx('btn', side === s && 'btn-active')}
              style={side === s ? { background: s === 'BUY' ? 'var(--up)' : 'var(--down)', borderColor: s === 'BUY' ? 'var(--up)' : 'var(--down)' } : { color: s === 'BUY' ? 'var(--up)' : 'var(--down)', borderColor: s === 'BUY' ? 'var(--up)' : 'var(--down)' }}
            >
              {s}
            </button>
          ))}
        </div>

        <label className="flex flex-col gap-1">
          <span className="tag">Shares</span>
          <input
            value={qty}
            onChange={(e) => { setQty(e.target.value.replace(/[^0-9.]/g, '')); setNote(null) }}
            inputMode="decimal"
            placeholder="0"
            className="mono text-[14px] px-2 py-1.5 rounded outline-none"
            style={{ background: 'var(--panel-2)', border: '1px solid var(--border-bright)', color: 'var(--text-bright)' }}
          />
        </label>

        <div className="rounded-md px-3 py-2 flex items-center justify-between" style={{ background: 'var(--panel-2)' }}>
          <span className="tag">Est. {side === 'BUY' ? 'cost' : 'proceeds'}</span>
          <span className="mono text-[14px]" style={{ color: 'var(--text-bright)' }}>{fmt(estimate)} <span className="dim text-[11px]">{stock.currency}</span></span>
        </div>

        <button
          onClick={submit}
          disabled={busy}
          className="btn"
          style={{ background: side === 'BUY' ? 'var(--up)' : 'var(--down)', borderColor: side === 'BUY' ? 'var(--up)' : 'var(--down)', color: 'var(--bg)', opacity: busy ? 0.6 : 1 }}
        >
          {busy ? '…' : `${side === 'BUY' ? 'Buy' : 'Sell'} ${stock.symbol}`}
        </button>

        {note && (
          <div className="text-[10px] leading-relaxed" style={{ color: note.ok ? 'var(--up)' : 'var(--down)' }}>{note.text}</div>
        )}

        <div className="dim text-[10px] leading-relaxed border-t pt-2" style={{ borderColor: 'var(--border)' }}>
          Paper fills at the latest close. Manage cash & positions in 💼 My Portfolio.
          Real trading via a broker comes in Phase 4.
        </div>
      </div>
    </div>
  )
}
