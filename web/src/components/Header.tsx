import { ThemeSwitcher } from './ThemeSwitcher'

export function Header() {
  const now = new Date().toLocaleTimeString('en-US', { hour12: false })
  return (
    <header className="flex items-center justify-between px-4 h-12 panel panel-glow shrink-0">
      <div className="flex items-center gap-3">
        <div className="live-dot" />
        <span className="mono font-bold tracking-widest text-[15px]" style={{ color: 'var(--text-bright)' }}>
          AI<span className="accent glow-accent">·</span>TERMINAL
        </span>
        <span className="tag hidden sm:inline">multi-agent market intelligence</span>
      </div>
      <div className="flex items-center gap-4">
        <span className="tag hidden md:inline">
          MKT <span className="up">OPEN</span> · {now} ET
        </span>
        <ThemeSwitcher />
      </div>
    </header>
  )
}
