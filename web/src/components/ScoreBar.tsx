import { motion } from 'framer-motion'

interface Props {
  label: string
  value: number
  max: number
  color?: string
}

export function ScoreBar({ label, value, max, color = 'var(--accent)' }: Props) {
  const ratio = Math.max(0, Math.min(1, value / max))
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="tag">{label}</span>
        <span className="mono text-[12px]" style={{ color: 'var(--text-bright)' }}>
          {value}
          <span className="dim text-[10px]">/{max}</span>
        </span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 10px ${color}` }}
          initial={{ width: 0 }}
          animate={{ width: `${ratio * 100}%` }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}
