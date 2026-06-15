import { useState } from 'react'
import clsx from 'clsx'
import type { FearGreed } from '../data/types'
import { useFearGreed } from '../data/hooks'

// CNN's five bands, by score. Color runs red (fear) → green (greed).
function band(score: number): { label: string; color: string } {
  if (score < 25) return { label: 'Extreme Fear', color: '#e5484d' }
  if (score < 45) return { label: 'Fear', color: '#f76b15' }
  if (score <= 55) return { label: 'Neutral', color: '#f5d90a' }
  if (score <= 75) return { label: 'Greed', color: '#46a758' }
  return { label: 'Extreme Greed', color: '#30a46c' }
}

// Title-cases CNN's lowercase rating ('extreme fear' → 'Extreme Fear') when present,
// else derives the band label from the score.
function ratingLabel(fg: FearGreed): string {
  if (fg.rating) return fg.rating.replace(/\b\w/g, (c) => c.toUpperCase())
  return fg.score != null ? band(fg.score).label : '—'
}

// Tiny inline sparkline of the trailing scores (0-100 → fixed y-axis so the trend is honest).
function Sparkline({ data, color, width = 96, height = 22 }: {
  data: number[]; color: string; width?: number; height?: number
}) {
  if (data.length < 2) return null
  const pad = 2
  const stepX = (width - pad * 2) / (data.length - 1)
  const y = (v: number) => height - pad - (Math.max(0, Math.min(100, v)) / 100) * (height - pad * 2)
  const pts = data.map((v, i) => `${pad + i * stepX},${y(v)}`).join(' ')
  return (
    <svg width={width} height={height} className="shrink-0" style={{ display: 'block' }}>
      {/* neutral (50) reference line */}
      <line x1={pad} x2={width - pad} y1={y(50)} y2={y(50)} stroke="var(--border)" strokeWidth={1} strokeDasharray="2 2" />
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={pad + (data.length - 1) * stepX} cy={y(data[data.length - 1])} r={1.8} fill={color} />
    </svg>
  )
}

function Hist({ label, value }: { label: string; value: number | null }) {
  if (value == null) return null
  const c = band(value)
  return (
    <div className="flex items-center gap-1.5">
      <span className="dim">{label}</span>
      <span className="mono" style={{ color: c.color }}>{Math.round(value)}</span>
    </div>
  )
}

// Full sentiment band — used at the top of the Market view.
export function FearGreedGauge({ data, loading }: { data?: FearGreed; loading?: boolean }) {
  const [open, setOpen] = useState(false)

  if (loading && !data) {
    return (
      <div className="px-4 py-2 border-b dim text-[11px]" style={{ borderColor: 'var(--border)' }}>
        Loading Fear &amp; Greed…
      </div>
    )
  }
  if (!data || data.score == null) return null

  const score = data.score
  const b = band(score)

  return (
    <div className="border-b" style={{ borderColor: 'var(--border)' }}>
      <div className="px-4 py-2 flex items-center gap-4 flex-wrap text-[12px]">
        {/* Score badge */}
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-2 shrink-0"
          title="CNN Fear & Greed Index — click for the seven indicators"
        >
          <span className="mono dim text-[10px] uppercase tracking-wide">Fear&nbsp;&amp;&nbsp;Greed</span>
          <span className="mono font-bold text-[18px]" style={{ color: b.color }}>{Math.round(score)}</span>
          <span className="mono text-[11px]" style={{ color: b.color }}>{ratingLabel(data)}</span>
          <span className="dim text-[10px]">{open ? '▴' : '▾'}</span>
        </button>

        {/* 3-month trend */}
        <Sparkline data={data.history} color={b.color} />

        {/* Gauge bar: red→yellow→green gradient with a marker at the score */}
        <div className="relative h-2 rounded-full flex-1 min-w-[160px]"
          style={{ background: 'linear-gradient(90deg,#e5484d 0%,#f76b15 25%,#f5d90a 50%,#46a758 75%,#30a46c 100%)' }}>
          <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
            style={{ left: `${score}%` }}>
            <div className="w-3 h-3 rounded-full border-2"
              style={{ background: 'var(--panel)', borderColor: 'var(--text-bright)' }} />
          </div>
        </div>

        {/* History */}
        <div className="flex items-center gap-4 shrink-0">
          <Hist label="Prev" value={data.previousClose} />
          <Hist label="1wk" value={data.previous1Week} />
          <Hist label="1mo" value={data.previous1Month} />
          <Hist label="1yr" value={data.previous1Year} />
        </div>
        {data.stale && <span className="dim text-[10px]" title="Live fetch failed; showing last cached reading">cached</span>}
      </div>

      {/* Expandable: the seven sub-indicators CNN derives the index from */}
      {open && data.components.length > 0 && (
        <div className="px-4 pb-2 flex flex-wrap gap-x-5 gap-y-1 text-[11px]">
          {data.components.map((c) => {
            const cb = c.score != null ? band(c.score) : null
            return (
              <div key={c.key} className="flex items-center gap-1.5">
                <span className="dim">{c.label}</span>
                <span className={clsx('mono')} style={{ color: cb?.color ?? 'var(--text-bright)' }}>
                  {c.score != null ? Math.round(c.score) : '—'}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// Compact inline read — market backdrop for a single stock (Stock Detail header).
// Self-fetching so callers don't need to thread the data through.
export function FearGreedBadge() {
  const { data } = useFearGreed()
  if (!data || data.score == null) return null
  const b = band(data.score)
  return (
    <div
      className="flex items-center gap-2 px-2 py-1 rounded"
      style={{ background: 'var(--panel-2)', border: '1px solid var(--border)' }}
      title={`CNN Fear & Greed Index: ${Math.round(data.score)} (${ratingLabel(data)}) — broad market backdrop`}
    >
      <span className="mono dim text-[9px] uppercase tracking-wide">Mkt</span>
      <span className="mono font-bold text-[13px]" style={{ color: b.color }}>{Math.round(data.score)}</span>
      <span className="mono text-[10px]" style={{ color: b.color }}>{ratingLabel(data)}</span>
      <Sparkline data={data.history} color={b.color} width={64} height={18} />
    </div>
  )
}
