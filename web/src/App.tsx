import { useEffect, useState } from 'react'
import { ThemeProvider, useTheme } from './themes/ThemeContext'
import { useStocks, useCandles } from './data/hooks'
import { Header } from './components/Header'
import { TickerTape } from './components/TickerTape'
import { Watchlist } from './components/Watchlist'
import { PriceChart } from './components/PriceChart'
import { AICallPanel } from './components/AICallPanel'
import { fmt, pct } from './util'

function Terminal() {
  const { theme } = useTheme()
  const { data: stocks, isLoading, isError, error } = useStocks()
  const [selected, setSelected] = useState<string | null>(null)

  // Default the selection to the top-ranked stock once data arrives.
  useEffect(() => {
    if (!selected && stocks && stocks.length) setSelected(stocks[0].symbol)
  }, [stocks, selected])

  const stock = stocks?.find((s) => s.symbol === selected) ?? stocks?.[0]
  const { data: candles } = useCandles(stock?.symbol)

  if (isLoading) return <CenterMsg title="CONNECTING" sub="Loading market data from the backend…" />
  if (isError) return <CenterMsg title="BACKEND OFFLINE" sub={`${(error as Error)?.message ?? 'Could not reach /api'} — is the Flask server running on :5000?`} />
  if (!stocks || !stocks.length || !stock) return <CenterMsg title="NO DATA" sub="The backend returned no analyzed stocks yet." />

  const up = stock.changePct >= 0

  return (
    <div className="scanlines relative h-full flex flex-col gap-2 p-2" style={{ zIndex: 1 }}>
      <Header />
      <TickerTape stocks={stocks} />

      <div className="flex gap-2 flex-1 min-h-0">
        <Watchlist stocks={stocks} selected={stock.symbol} onSelect={setSelected} />

        {/* Center: symbol header + chart */}
        <main className="panel panel-glow flex-1 flex flex-col min-w-0 overflow-hidden">
          <div className="px-4 py-3 border-b flex items-end justify-between flex-wrap gap-3" style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-baseline gap-3">
              <h1 className="mono font-bold text-[26px] tracking-wide" style={{ color: 'var(--text-bright)' }}>
                {stock.symbol}
              </h1>
              <span className="dim text-[13px]">{stock.name}</span>
              <span className="tag">{stock.sector}</span>
            </div>
            <div className="flex items-baseline gap-3">
              <span className="mono text-[26px]" style={{ color: 'var(--text-bright)' }}>
                {fmt(stock.price)}
              </span>
              <span className="dim text-[12px]">{stock.currency}</span>
              <span className={`mono text-[16px] ${up ? 'up' : 'down'}`}>
                {up ? '▲' : '▼'} {pct(stock.changePct)}
              </span>
            </div>
          </div>
          <div className="flex-1 min-h-0 p-2">
            <PriceChart candles={candles ?? []} themeKey={theme} />
          </div>
        </main>

        {/* key by symbol so the agent switcher resets to the default when you change stocks */}
        <AICallPanel key={stock.symbol} stock={stock} />
      </div>
    </div>
  )
}

function CenterMsg({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="scanlines relative h-full flex items-center justify-center p-6" style={{ zIndex: 1 }}>
      <div className="panel panel-glow px-8 py-6 text-center max-w-md">
        <div className="mono font-bold tracking-widest text-[20px]" style={{ color: 'var(--text-bright)' }}>{title}</div>
        <div className="dim text-[12px] mt-2 leading-relaxed">{sub}</div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <div className="grid-bg" />
      <Terminal />
    </ThemeProvider>
  )
}
