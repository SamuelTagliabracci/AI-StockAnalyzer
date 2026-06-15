import { useState } from 'react'
import { ThemeProvider } from './themes/ThemeContext'
import { useStocks } from './data/hooks'
import { Header } from './components/Header'
import { TickerTape } from './components/TickerTape'
import { Watchlist } from './components/Watchlist'
import { SmartMoney } from './components/SmartMoney'
import { MarketView } from './components/MarketView'
import { StockDetail } from './components/StockDetail'
import { AITraders } from './components/AITraders'
import { Portfolio } from './components/Portfolio'
import clsx from 'clsx'

// Market is the front door; Detail is reached by clicking a stock (no top-level tab).
type View = 'market' | 'detail' | 'feed' | 'traders' | 'portfolio'

const NAV: { key: View; label: string; live?: boolean }[] = [
  { key: 'market', label: '🏛 Market' },
  { key: 'feed', label: '💰 Smart Money', live: true },
  { key: 'traders', label: '🤖 AI Traders' },
  { key: 'portfolio', label: '💼 My Portfolio' },
]

function Terminal() {
  const { data: stocks, isLoading, isError, error } = useStocks()
  const [view, setView] = useState<View>('market')
  const [selected, setSelected] = useState<string | null>(null)
  // In feed view the watchlist filters the Smart Money feed; null = whole market.
  const [feedSymbol, setFeedSymbol] = useState<string | null>(null)

  if (isLoading) return <CenterMsg title="CONNECTING" sub="Loading market data from the backend…" />
  if (isError) return <CenterMsg title="BACKEND OFFLINE" sub={`${(error as Error)?.message ?? 'Could not reach /api'} — is the Flask server running on :5000?`} />
  if (!stocks || !stocks.length) return <CenterMsg title="NO DATA" sub="The backend returned no analyzed stocks yet." />

  const detailStock = stocks.find((s) => s.symbol === selected)

  function openDetail(symbol: string) {
    setSelected(symbol)
    setView('detail')
  }

  return (
    <div className="scanlines relative h-full flex flex-col gap-2 p-2" style={{ zIndex: 1 }}>
      <Header />
      <TickerTape stocks={stocks} />

      {/* Top-level navigation — prominent .btn tabs. */}
      <div className="flex items-center gap-2">
        {NAV.map((n) => (
          <button
            key={n.key}
            onClick={() => setView(n.key)}
            className={clsx('btn flex items-center gap-1.5', view === n.key && 'btn-active')}
          >
            {n.label}
            {n.live && <span className="live-dot" />}
          </button>
        ))}
        {view === 'detail' && detailStock && (
          <span className="dim text-[11px]">viewing {detailStock.symbol} — pick another from 🏛 Market</span>
        )}
        {view === 'feed' && (
          <span className="dim text-[11px]">
            {feedSymbol ? `showing ${feedSymbol} — click a different ticker or “✕” for the whole market` : 'whole market — click a ticker to filter'}
          </span>
        )}
      </div>

      {view === 'market' && (
        <div className="flex gap-2 flex-1 min-h-0">
          <MarketView stocks={stocks} onSelectSymbol={openDetail} />
        </div>
      )}

      {view === 'detail' && (
        <div className="flex gap-2 flex-1 min-h-0">
          {detailStock
            ? <StockDetail stock={detailStock} onBack={() => setView('market')} />
            : <CenterMsg title="PICK A STOCK" sub="Choose a stock from the Market view to see its detail." />}
        </div>
      )}

      {view === 'feed' && (
        <div className="flex gap-2 flex-1 min-h-0">
          <Watchlist stocks={stocks} selected={feedSymbol ?? ''} onSelect={setFeedSymbol} />
          <SmartMoney symbol={feedSymbol} onClearSymbol={() => setFeedSymbol(null)} />
        </div>
      )}

      {view === 'traders' && (
        <div className="flex gap-2 flex-1 min-h-0">
          <AITraders onSelectSymbol={openDetail} />
        </div>
      )}

      {view === 'portfolio' && (
        <div className="flex gap-2 flex-1 min-h-0">
          <Portfolio onSelectSymbol={openDetail} />
        </div>
      )}
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
