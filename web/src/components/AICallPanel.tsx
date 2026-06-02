import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'
import type { Stock } from '../data/types'
import { fmt, pct, actionColor } from '../util'
import { ScoreBar } from './ScoreBar'

export function AICallPanel({ stock }: { stock: Stock }) {
  // verdicts[] is the multi-agent ledger; fall back to the single call for old payloads.
  const verdicts = stock.verdicts?.length ? stock.verdicts : [stock.call]

  // Default to Claude Code's call when present (the premium analyst), else the first.
  const defaultIdx = useMemo(() => {
    const i = verdicts.findIndex((v) => v.agent === 'Claude Code')
    return i >= 0 ? i : 0
  }, [verdicts])

  // Reset selection to the default whenever the stock (and thus its verdicts) changes.
  const [selected, setSelected] = useState(defaultIdx)
  const idx = selected < verdicts.length ? selected : defaultIdx
  const c = verdicts[idx]
  const color = actionColor(c.action)
  const hasScores = c.totalScore != null // quant-only breakdown

  return (
    <div className="panel panel-glow flex flex-col w-[300px] shrink-0 overflow-hidden">
      <div className="px-3 py-2 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
        <span className="tag">AI Verdict</span>
        <span className="tag accent">{verdicts.length} agent{verdicts.length > 1 ? 's' : ''}</span>
      </div>

      {/* Agent switcher — one pill per competing agent */}
      <div className="flex gap-1 px-3 py-2 border-b overflow-x-auto" style={{ borderColor: 'var(--border)' }}>
        {verdicts.map((v, i) => (
          <button
            key={v.agent}
            onClick={() => setSelected(i)}
            className={clsx('tag whitespace-nowrap px-2 py-1 rounded transition-opacity', i === idx ? 'accent' : 'opacity-50 hover:opacity-80')}
            style={i === idx ? { borderColor: actionColor(v.action), color: actionColor(v.action) } : undefined}
            title={`${v.agent}: ${v.action}`}
          >
            {v.agent}
          </button>
        ))}
      </div>

      <div className="p-4 flex flex-col gap-4 overflow-y-auto">
        {/* Headline call */}
        <motion.div
          key={`${c.agent}-${c.action}`}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-md px-3 py-3 text-center"
          style={{ border: `1px solid ${color}`, boxShadow: `0 0 22px -6px ${color}`, background: 'color-mix(in srgb, var(--panel-2) 80%, black)' }}
        >
          <div className="mono font-bold tracking-widest text-[22px]" style={{ color }}>
            {c.action}
          </div>
          <div className="tag mt-1">
            confidence {Math.round(c.confidence * 100)}%
            {c.horizon ? ` · ${c.horizon}` : ''}
          </div>
        </motion.div>

        {/* Price targets */}
        <div className="grid grid-cols-2 gap-2">
          <Stat label="Current" value={fmt(c.currentPrice)} sub={stock.currency} />
          <Stat label="Target" value={fmt(c.targetPrice)} sub={pct(c.upsidePct)} subColor={c.upsidePct >= 0 ? 'var(--up)' : 'var(--down)'} />
        </div>

        {/* Composite score + sub-scores — quant engine only */}
        {hasScores ? (
          <>
            <div className="flex items-center justify-between rounded-md px-3 py-2" style={{ background: 'var(--panel-2)' }}>
              <span className="tag">Composite</span>
              <span className="mono text-[20px]" style={{ color: 'var(--text-bright)' }}>
                {c.totalScore}<span className="dim text-[12px]">/100</span>
              </span>
            </div>
            <div className="flex flex-col gap-3">
              <ScoreBar label="Fundamental" value={c.fundamentalScore ?? 0} max={40} color="var(--accent)" />
              <ScoreBar label="Technical" value={c.technicalScore ?? 0} max={30} color="var(--up)" />
              <ScoreBar label="Momentum" value={c.momentumScore ?? 0} max={30} color="var(--warn)" />
              <ScoreBar label="Risk" value={c.riskScore ?? 0} max={100} color="var(--down)" />
            </div>
          </>
        ) : (
          <div className="tag dim">{c.agent} · reasoned call (no quant sub-scores)</div>
        )}

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
