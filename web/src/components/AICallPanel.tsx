import { motion } from 'framer-motion'
import type { Stock } from '../data/types'
import { fmt, pct, actionColor } from '../util'
import { ScoreBar } from './ScoreBar'

export function AICallPanel({ stock }: { stock: Stock }) {
  const c = stock.call
  const color = actionColor(c.action)
  return (
    <div className="panel panel-glow flex flex-col w-[300px] shrink-0 overflow-hidden">
      <div className="px-3 py-2 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
        <span className="tag">AI Verdict</span>
        <span className="tag accent">{c.agent}</span>
      </div>

      <div className="p-4 flex flex-col gap-4 overflow-y-auto">
        {/* Headline call */}
        <motion.div
          key={c.action}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-md px-3 py-3 text-center"
          style={{ border: `1px solid ${color}`, boxShadow: `0 0 22px -6px ${color}`, background: 'color-mix(in srgb, var(--panel-2) 80%, black)' }}
        >
          <div className="mono font-bold tracking-widest text-[22px]" style={{ color }}>
            {c.action}
          </div>
          <div className="tag mt-1">confidence {Math.round(c.confidence * 100)}%</div>
        </motion.div>

        {/* Price targets */}
        <div className="grid grid-cols-2 gap-2">
          <Stat label="Current" value={fmt(c.currentPrice)} sub={stock.currency} />
          <Stat label="Target" value={fmt(c.targetPrice)} sub={pct(c.upsidePct)} subColor={c.upsidePct >= 0 ? 'var(--up)' : 'var(--down)'} />
        </div>

        {/* Composite score */}
        <div className="flex items-center justify-between rounded-md px-3 py-2" style={{ background: 'var(--panel-2)' }}>
          <span className="tag">Composite</span>
          <span className="mono text-[20px]" style={{ color: 'var(--text-bright)' }}>
            {c.totalScore}<span className="dim text-[12px]">/100</span>
          </span>
        </div>

        {/* Sub-scores */}
        <div className="flex flex-col gap-3">
          <ScoreBar label="Fundamental" value={c.fundamentalScore} max={40} color="var(--accent)" />
          <ScoreBar label="Technical" value={c.technicalScore} max={30} color="var(--up)" />
          <ScoreBar label="Momentum" value={c.momentumScore} max={30} color="var(--warn)" />
          <ScoreBar label="Risk" value={c.riskScore} max={100} color="var(--down)" />
        </div>

        {/* Rationale */}
        <div className="rounded-md px-3 py-2 text-[11px] leading-relaxed dim" style={{ background: 'var(--panel-2)', borderLeft: `2px solid ${color}` }}>
          {c.rationale}
        </div>

        {/* HITL actions (wired later to the approval queue) */}
        <div className="grid grid-cols-2 gap-2">
          <button className="btn" style={{ borderColor: 'var(--up)', color: 'var(--up)' }}>Approve · Paper</button>
          <button className="btn">Skip</button>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value, sub, subColor }: { label: string; value: string; sub?: string; subColor?: string }) {
  return (
    <div className="rounded-md px-3 py-2" style={{ background: 'var(--panel-2)' }}>
      <div className="tag">{label}</div>
      <div className="mono text-[16px]" style={{ color: 'var(--text-bright)' }}>{value}</div>
      {sub && <div className="mono text-[11px]" style={{ color: subColor ?? 'var(--text-dim)' }}>{sub}</div>}
    </div>
  )
}
