import { useEffect, useMemo, useRef } from 'react';
import {
  ColorType,
  createChart,
  CrosshairMode,
  type HistogramData,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts';
import { useTheme } from '@/providers/ThemeProvider';
import { cn } from '@/lib/utils/cn';
import type { OHLCVRow } from '@/lib/types';

interface MACDChartProps {
  /** Full history. MACD/EMA warm-up uses this — don't slice before passing. */
  rows: OHLCVRow[];
  fastPeriod?: number;
  slowPeriod?: number;
  signalPeriod?: number;
  /** Zoom the visible time axis without trimming data. */
  visibleRange?: { from: UTCTimestamp; to: UTCTimestamp };
  height?: number;
  className?: string;
}

const MACD_COLOR = '#60a5fa'; // blue-400
const SIGNAL_COLOR = '#f59e0b'; // amber-500
const POS = '#22c55e';
const NEG = '#ef4444';

export function MACDChart({
  rows,
  fastPeriod = 12,
  slowPeriod = 26,
  signalPeriod = 9,
  visibleRange,
  height = 160,
  className,
}: MACDChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const macdRef = useRef<ISeriesApi<'Line'> | null>(null);
  const signalRef = useRef<ISeriesApi<'Line'> | null>(null);
  const histRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const { resolvedTheme } = useTheme();

  const series = useMemo(
    () => computeMacdSeries(rows, fastPeriod, slowPeriod, signalPeriod),
    [rows, fastPeriod, slowPeriod, signalPeriod],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: resolvedTheme === 'dark' ? '#cbd5e1' : '#334155',
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: resolvedTheme === 'dark' ? '#1e293b' : '#e2e8f0' },
        horzLines: { color: resolvedTheme === 'dark' ? '#1e293b' : '#e2e8f0' },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: false, secondsVisible: false },
      crosshair: { mode: CrosshairMode.Normal },
    });

    const macdLine = chart.addLineSeries({
      color: MACD_COLOR,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const signalLine = chart.addLineSeries({
      color: SIGNAL_COLOR,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const hist = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      base: 0,
    });
    hist.priceScale().applyOptions({ scaleMargins: { top: 0.1, bottom: 0 } });

    chartRef.current = chart;
    macdRef.current = macdLine;
    signalRef.current = signalLine;
    histRef.current = hist;

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      macdRef.current = null;
      signalRef.current = null;
      histRef.current = null;
    };
  }, [height, resolvedTheme]);

  useEffect(() => {
    macdRef.current?.setData(series.macd);
    signalRef.current?.setData(series.signal);
    histRef.current?.setData(series.histogram);
  }, [series]);

  // Apply the visible time range (or fit all) — kept in sync with the price
  // chart in StockDetail so the two panels share the same x-axis window.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || series.macd.length === 0) return;
    if (!visibleRange) {
      chart.timeScale().fitContent();
      return;
    }
    const firstTime = series.macd[0]!.time as UTCTimestamp;
    const lastTime = series.macd[series.macd.length - 1]!.time as UTCTimestamp;
    const from = Math.max(visibleRange.from, firstTime) as UTCTimestamp;
    const to = Math.min(visibleRange.to, lastTime) as UTCTimestamp;
    if (from >= to) {
      chart.timeScale().fitContent();
    } else {
      chart.timeScale().setVisibleRange({ from, to });
    }
  }, [visibleRange, series]);

  return <div ref={containerRef} className={cn('w-full', className)} style={{ height }} />;
}

// ——— helpers ———

function toUnix(iso: string): Time {
  const ts = Math.floor(new Date(`${iso}T00:00:00Z`).getTime() / 1000);
  return ts as UTCTimestamp;
}

function ema(values: number[], period: number): Array<number | null> {
  const out: Array<number | null> = [];
  const k = 2 / (period + 1);
  let prev: number | null = null;
  let seed = 0;
  for (let i = 0; i < values.length; i++) {
    const v = values[i]!;
    if (i < period - 1) {
      seed += v;
      out.push(null);
    } else if (i === period - 1) {
      seed += v;
      prev = seed / period;
      out.push(prev);
    } else {
      prev = v * k + (prev ?? v) * (1 - k);
      out.push(prev);
    }
  }
  return out;
}

function emaFromNullable(values: Array<number | null>, period: number): Array<number | null> {
  const out: Array<number | null> = Array(values.length).fill(null);
  const k = 2 / (period + 1);
  let prev: number | null = null;
  let seedCount = 0;
  let seedSum = 0;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v == null) continue;
    if (prev === null) {
      seedSum += v;
      seedCount += 1;
      if (seedCount === period) {
        prev = seedSum / period;
        out[i] = prev;
      }
    } else {
      prev = v * k + prev * (1 - k);
      out[i] = prev;
    }
  }
  return out;
}

function computeMacdSeries(
  rows: OHLCVRow[],
  fastPeriod: number,
  slowPeriod: number,
  signalPeriod: number,
): { macd: LineData[]; signal: LineData[]; histogram: HistogramData[] } {
  const closes = rows.map((r) => r.close);
  const times = rows.map((r) => toUnix(r.date));
  const fast = ema(closes, fastPeriod);
  const slow = ema(closes, slowPeriod);
  const macdLine: Array<number | null> = closes.map((_, i) => {
    const f = fast[i];
    const s = slow[i];
    return f != null && s != null ? f - s : null;
  });
  const signalLine = emaFromNullable(macdLine, signalPeriod);

  const macd: LineData[] = [];
  const signal: LineData[] = [];
  const histogram: HistogramData[] = [];
  for (let i = 0; i < closes.length; i++) {
    const t = times[i]!;
    const m = macdLine[i];
    const s = signalLine[i];
    if (m != null) macd.push({ time: t, value: m });
    if (s != null) signal.push({ time: t, value: s });
    if (m != null && s != null) {
      const h = m - s;
      histogram.push({
        time: t,
        value: h,
        color: h >= 0 ? `${POS}99` : `${NEG}99`,
      });
    }
  }
  return { macd, signal, histogram };
}
