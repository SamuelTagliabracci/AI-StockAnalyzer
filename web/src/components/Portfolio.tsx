import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAccounts } from '../data/hooks'
import { setCash, setHolding } from '../data/api'
import { AccountPortfolio } from './AccountPortfolio'

// Sam's own account. Stub auth for now — we just resolve the single 'human' account.
// Manual entry lets you mirror your Wealthsimple cash + existing positions.
export function Portfolio({ onSelectSymbol }: { onSelectSymbol?: (s: string) => void }) {
  const { data: accounts, isLoading } = useAccounts()
  const qc = useQueryClient()
  const human = (accounts ?? []).find((a) => a.type === 'human')

  if (isLoading) return <Shell><div className="dim text-[12px] p-6">Loading…</div></Shell>
  if (!human) return <Shell><div className="dim text-[12px] p-6">No account found. Run the seed script.</div></Shell>

  function refresh() {
    qc.invalidateQueries({ queryKey: ['accounts'] })
    qc.invalidateQueries({ queryKey: ['portfolio', human!.id] })
  }

  return (
    <Shell email={human.email}>
      <div className="flex-1 min-h-0 flex">
        <div className="flex-1 min-w-0 overflow-y-auto">
          <AccountPortfolio accountId={human.id} onSelectSymbol={onSelectSymbol} />
        </div>
        <div className="w-[260px] shrink-0 border-l overflow-y-auto" style={{ borderColor: 'var(--border)' }}>
          <ManualEntry accountId={human.id} onDone={refresh} />
        </div>
      </div>
    </Shell>
  )
}

function Shell({ children, email }: { children: React.ReactNode; email?: string | null }) {
  return (
    <main className="panel panel-glow flex-1 flex flex-col min-w-0 overflow-hidden">
      <div className="px-4 py-3 border-b flex items-center gap-3" style={{ borderColor: 'var(--border)' }}>
        <h1 className="mono font-bold text-[20px] tracking-wide" style={{ color: 'var(--text-bright)' }}>MY PORTFOLIO</h1>
        {email && <span className="tag">signed in as {email}</span>}
        <span className="dim text-[11px]">paper · you approve your own trades</span>
      </div>
      {children}
    </main>
  )
}

function ManualEntry({ accountId, onDone }: { accountId: number; onDone: () => void }) {
  const [currency, setCurrency] = useState('USD')
  const [cash, setCashAmt] = useState('')
  const [sym, setSym] = useState('')
  const [shares, setShares] = useState('')
  const [avg, setAvg] = useState('')
  const [msg, setMsg] = useState<string | null>(null)

  async function saveCash() {
    if (!cash) return
    await setCash(accountId, currency, Number(cash))
    setMsg(`Set ${currency} cash to ${Number(cash).toLocaleString()}.`)
    setCashAmt('')
    onDone()
  }
  async function saveHolding() {
    if (!sym || !shares) return
    await setHolding(accountId, sym.toUpperCase(), Number(shares), Number(avg) || 0)
    setMsg(`Set ${sym.toUpperCase()} = ${shares} sh @ ${avg || 0}.`)
    setSym(''); setShares(''); setAvg('')
    onDone()
  }

  return (
    <div className="flex flex-col">
      <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
        <span className="tag">Manual entry</span>
        <div className="dim text-[10px] mt-1">Mirror your Wealthsimple cash & existing positions (no trade is executed).</div>
      </div>

      <div className="p-3 flex flex-col gap-2 border-b" style={{ borderColor: 'var(--border)' }}>
        <span className="tag">Set cash</span>
        <div className="flex gap-1.5">
          {['USD', 'CAD'].map((c) => (
            <button key={c} onClick={() => setCurrency(c)} className={`tag ${currency === c ? 'row-active' : ''}`}>{c}</button>
          ))}
        </div>
        <Input value={cash} onChange={setCashAmt} placeholder="amount" />
        <button onClick={saveCash} className="btn">Save cash</button>
      </div>

      <div className="p-3 flex flex-col gap-2">
        <span className="tag">Add / set position</span>
        <Input value={sym} onChange={setSym} placeholder="ticker (e.g. MU)" />
        <Input value={shares} onChange={setShares} placeholder="shares" />
        <Input value={avg} onChange={setAvg} placeholder="avg cost (optional)" />
        <button onClick={saveHolding} className="btn">Save position</button>
      </div>

      {msg && <div className="dim text-[10px] px-3 pb-3">{msg}</div>}
    </div>
  )
}

function Input({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="mono text-[12px] px-2 py-1.5 rounded outline-none w-full"
      style={{ background: 'var(--panel-2)', border: '1px solid var(--border-bright)', color: 'var(--text-bright)' }}
    />
  )
}
