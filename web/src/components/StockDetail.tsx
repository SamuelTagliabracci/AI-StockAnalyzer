import { useState } from 'react'
import clsx from 'clsx'
import { useTheme } from '../themes/ThemeContext'
import type { Stock } from '../data/types'
import { useCandles, useNews, useSignals } from '../data/hooks'
import { fmt, pct, money, compact, actionColor, timeAgo } from '../util'
import { PriceChart } from './PriceChart'
import { TradeTicket } from './TradeTicket'
import { FearGreedBadge } from './FearGreedGauge'

type Tab = 'overview' | 'news' | 'pros' | 'agents'
const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'news', label: 'News & Filings' },
  { key: 'pros', label: 'Pro Traders' },
  { key: 'agents', label: 'AI Agents' },
]

// Chart range options → trading-day counts for /api/candles.
const RANGES: { label: string; days: number }[] = [
  { label: '1M', days: 22 },
  { label: '6M', days: 126 },
  { label: '1Y', days: 252 },
  { label: '5Y', days: 1260 },
  { label: 'MAX', days: 7300 },
]

export function StockDetail({ stock, onBack }: { stock: Stock; onBack: () => void }) {
  const [tab, setTab] = useState<Tab>('overview')
  const up = stock.changePct >= 0

  return (
    <main className="panel panel-glow flex-1 flex flex-col min-w-0 overflow-hidden">
      {/* Header: back, identity, price, trade actions */}
      <div className="px-4 py-3 border-b flex items-center justify-between flex-wrap gap-3" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={onBack} className="btn" title="Back to Market">← Market</button>
          <h1 className="mono font-bold text-[26px] tracking-wide" style={{ color: 'var(--text-bright)' }}>{stock.symbol}</h1>
          <span className="tag text-[9px]">{stock.exchange}</span>
          <span className="dim text-[13px] truncate">{stock.name}</span>
          <span className="tag">{stock.sector}</span>
        </div>
        <div className="flex items-center gap-4">
          {/* Market backdrop for this name's verdict */}
          <FearGreedBadge />
          <div className="text-right">
            <div className="mono text-[24px]" style={{ color: 'var(--text-bright)' }}>{fmt(stock.price)} <span className="dim text-[12px]">{stock.currency}</span></div>
            <div className={clsx('mono text-[14px]', up ? 'up' : 'down')}>{up ? '▲' : '▼'} {pct(stock.changePct)}</div>
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="px-3 py-2 border-b flex items-center gap-1.5 flex-wrap" style={{ borderColor: 'var(--border)' }}>
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} className={clsx('btn', tab === t.key && 'btn-active')}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Body: tab content (left/main) + persistent trade ticket (right) */}
      <div className="flex-1 min-h-0 flex">
        <div className="flex-1 min-w-0 overflow-y-auto">
          {tab === 'overview' && <Overview stock={stock} />}
          {tab === 'news' && <News symbol={stock.symbol} />}
          {tab === 'pros' && <ProTraders symbol={stock.symbol} />}
          {tab === 'agents' && <Agents stock={stock} />}
        </div>
        <div className="w-[260px] shrink-0 border-l overflow-y-auto" style={{ borderColor: 'var(--border)' }}>
          <TradeTicket stock={stock} />
        </div>
      </div>
    </main>
  )
}

function Overview({ stock }: { stock: Stock }) {
  const { theme } = useTheme()
  const [days, setDays] = useState(252)
  const { data: candles, isLoading } = useCandles(stock.symbol, days)
  const c = stock.call

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 flex items-center gap-1.5 border-b" style={{ borderColor: 'var(--border)' }}>
        <span className="tag mr-1">Range</span>
        {RANGES.map((r) => (
          <button key={r.label} onClick={() => setDays(r.days)} className={clsx('tag', days === r.days && 'row-active')}>{r.label}</button>
        ))}
      </div>
      <div className="h-[320px] p-2 shrink-0">
        {isLoading ? <Center>Loading chart…</Center> : <PriceChart candles={candles ?? []} themeKey={`${theme}-${days}`} />}
      </div>
      {/* Key stats */}
      <div className="grid gap-2 p-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))' }}>
        <Stat label="Price" value={`${fmt(stock.price)} ${stock.currency}`} />
        <Stat label="Change" value={pct(stock.changePct)} cls={stock.changePct >= 0 ? 'up' : 'down'} />
        <Stat label="Volume" value={compact(stock.volume ?? null)} />
        <Stat label="Rel Volume" value={stock.relVolume != null ? `${fmt(stock.relVolume, 2)}×` : '—'} />
        <Stat label="Quant Score" value={c.totalScore != null ? `${c.totalScore}/100` : '—'} />
        <Stat label="Quant Call" value={c.action} cls={undefined} accent />
        <Stat label="Target" value={c.targetPrice ? fmt(c.targetPrice) : '—'} sub={c.targetPrice ? pct(c.upsidePct) : undefined} subCls={c.upsidePct >= 0 ? 'up' : 'down'} />
      </div>
    </div>
  )
}

function News({ symbol }: { symbol: string }) {
  const { data: news, isLoading, isError } = useNews(symbol)
  if (isLoading) return <Center>Loading news…</Center>
  if (isError) return <Center>Couldn't load news.</Center>
  if (!news || news.length === 0) return <Center>No recent news for {symbol}.</Center>
  return (
    <div className="flex flex-col">
      {news.map((n) => (
        <a key={n.id ?? n.url} href={n.url ?? '#'} target="_blank" rel="noreferrer"
           className="row-hover px-4 py-3 border-b flex gap-3" style={{ borderColor: 'var(--border)' }}>
          {n.thumbnail && <img src={n.thumbnail} alt="" className="w-20 h-14 object-cover rounded shrink-0" style={{ border: '1px solid var(--border)' }} />}
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              {n.kind === 'announcement' && <span className="tag accent text-[8px]">ANNOUNCEMENT</span>}
              {n.kind === 'video' && <span className="tag text-[8px]">VIDEO</span>}
              <span className="dim text-[10px]">{n.publisher} · {timeAgo(n.published_at)}</span>
            </div>
            <div className="text-[13px] leading-snug" style={{ color: 'var(--text-bright)' }}>{n.title}</div>
            {n.summary && <div className="dim text-[11px] mt-1 line-clamp-2">{n.summary}</div>}
          </div>
        </a>
      ))}
    </div>
  )
}

function ProTraders({ symbol }: { symbol: string }) {
  const { data: signals, isLoading } = useSignals({ symbol })
  if (isLoading) return <Center>Loading trades…</Center>
  if (!signals || signals.length === 0)
    return <Center>No disclosed insider / institutional trades for {symbol} yet. (US issuers file with the SEC; Canadian names file with SEDI, which has no public feed.)</Center>
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="dim text-[10px] uppercase tracking-wider sticky top-0" style={{ background: 'var(--panel)' }}>
          <th className="text-left font-normal px-4 py-2">Filed</th>
          <th className="text-left font-normal px-3 py-2">Who</th>
          <th className="text-left font-normal px-3 py-2">Action</th>
          <th className="text-right font-normal px-3 py-2">Shares</th>
          <th className="text-right font-normal px-4 py-2">Value</th>
        </tr>
      </thead>
      <tbody>
        {signals.map((s, i) => {
          const buy = s.action === 'BUY'
          return (
            <tr key={i} className="row-hover border-b" style={{ borderColor: 'var(--border)' }}>
              <td className="mono text-[11px] px-4 py-2 dim whitespace-nowrap">{s.filedAt ?? '—'}</td>
              <td className="px-3 py-2">
                <div className="text-[12px]">{s.actor}</div>
                <div className="dim text-[10px]">{s.actorRole}</div>
              </td>
              <td className={clsx('mono text-[12px] px-3 py-2', buy ? 'up' : 'down')}>{buy ? '▲ BUY' : '▼ SELL'}</td>
              <td className="mono text-[12px] px-3 py-2 text-right">{compact(s.shares)}</td>
              <td className="mono text-[12px] px-4 py-2 text-right" style={{ color: 'var(--text-bright)' }}>{money(s.valueUsd)}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function Agents({ stock }: { stock: Stock }) {
  const verdicts = stock.verdicts?.length ? stock.verdicts : [stock.call]
  return (
    <div className="flex flex-col">
      <div className="px-4 py-2 dim text-[10px] border-b" style={{ borderColor: 'var(--border)' }}>
        Each agent's latest read on {stock.symbol}. Their paper positions & P&L arrive with the trading engine (Phase 3).
      </div>
      <div className="grid gap-3 p-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
        {verdicts.map((v) => {
          const color = actionColor(v.action)
          return (
            <section key={v.agent} className="panel overflow-hidden">
              <div className="px-3 py-2 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
                <span className="mono text-[13px]" style={{ color: 'var(--text-bright)' }}>{v.agent}</span>
                <span className="mono text-[13px] font-bold" style={{ color }}>{v.action}</span>
              </div>
              <div className="p-3 flex flex-col gap-2">
                <div className="flex items-center gap-3 text-[11px]">
                  <span className="tag">conf {Math.round(v.confidence * 100)}%</span>
                  {v.horizon && <span className="tag">{v.horizon}</span>}
                  {v.targetPrice ? (
                    <span className="dim">target <span className="mono" style={{ color: 'var(--text-bright)' }}>{fmt(v.targetPrice)}</span> <span className={v.upsidePct >= 0 ? 'up' : 'down'}>{pct(v.upsidePct)}</span></span>
                  ) : null}
                </div>
                {v.rationale && (
                  <div className="text-[11px] leading-relaxed dim" style={{ borderLeft: `2px solid ${color}`, paddingLeft: 8 }}>{v.rationale}</div>
                )}
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )
}

function Stat({ label, value, sub, cls, subCls, accent }: { label: string; value: string; sub?: string; cls?: string; subCls?: string; accent?: boolean }) {
  return (
    <div className="rounded-md px-3 py-2" style={{ background: 'var(--panel-2)' }}>
      <div className="tag">{label}</div>
      <div className={clsx('mono text-[15px]', cls)} style={accent ? { color: 'var(--accent)' } : !cls ? { color: 'var(--text-bright)' } : undefined}>{value}</div>
      {sub && <div className={clsx('mono text-[11px]', subCls)}>{sub}</div>}
    </div>
  )
}

function Center({ children }: { children: React.ReactNode }) {
  return <div className="h-full flex items-center justify-center dim text-[12px] p-6 text-center">{children}</div>
}
