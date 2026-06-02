import { useEffect, useRef } from 'react'
import { createChart, CandlestickSeries, ColorType, type IChartApi, type Time } from 'lightweight-charts'
import type { Candle } from '../data/types'
import { cssVar } from '../util'

interface Props {
  candles: Candle[]
  themeKey: string // re-create chart when theme changes so colors update
}

export function PriceChart({ candles, themeKey }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const el = ref.current

    const chart: IChartApi = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: cssVar('--text-dim'),
        fontFamily: cssVar('--font-mono'),
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: cssVar('--border') },
        horzLines: { color: cssVar('--border') },
      },
      rightPriceScale: { borderColor: cssVar('--border') },
      timeScale: { borderColor: cssVar('--border'), timeVisible: false },
      crosshair: {
        vertLine: { color: cssVar('--accent'), labelBackgroundColor: cssVar('--accent') },
        horzLine: { color: cssVar('--accent'), labelBackgroundColor: cssVar('--accent') },
      },
    })

    const up = cssVar('--up')
    const down = cssVar('--down')
    const series = chart.addSeries(CandlestickSeries, {
      upColor: up,
      downColor: down,
      borderUpColor: up,
      borderDownColor: down,
      wickUpColor: up,
      wickDownColor: down,
    })
    series.setData(
      candles.map((c) => ({
        time: c.time as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    )
    chart.timeScale().fitContent()

    return () => chart.remove()
  }, [candles, themeKey])

  return <div ref={ref} className="w-full h-full" />
}
