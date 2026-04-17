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

export type OverlayKey = 'sma20' | 'sma50' | 'sma200' | 'ema12' | 'ema26';

interface PriceChartProps {
  rows: OHLCVRow[];
  overlays: Partial<Record<OverlayKey, boolean>>;
  className?: string;
  height?: number;
}

const OVERLAY_COLORS: Record<OverlayKey, string> = {
  sma20: '#60a5fa', // blue-400
  sma50: '#f59e0b', // amber-500
  sma200: '#a855f7', // purple-500
  ema12: '#22d3ee', // cyan-400
  ema26: '#f472b6', // pink-400
};

const OVERLAY_SPECS: Array<{ key: OverlayKey; period: number; type: 'sma' | 'ema' }> = [
  { key: 'sma20', period: 20, type: 'sma' },
  { key: 'sma50', period: 50, type: 'sma' },
  { key: 'sma200', period: 200, type: 'sma' },
  { key: 'ema12', period: 12, type: 'ema' },
  { key: 'ema26', period: 26, type: 'ema' },
];

const UP_COLOR = '#22c55e';
const DOWN_COLOR = '#ef4444';

export function PriceChart({ rows, overlays, className, height = 480 }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const overlayRefs = useRef<Partial<Record<OverlayKey, ISeriesApi<'Line'>>>>({});
  const { resolvedTheme } = useTheme();

  // Precompute candle + volume + overlay series data (no side effects).
  const candleData = useMemo(
    () =>
      rows.map((r) => ({
        time: toUnix(r.date),
        open: r.open,
        high: r.high,
        low: r.low,
        close: r.close,
      })),
    [rows],
  );
  const volumeData = useMemo<HistogramData[]>(
    () =>
      rows.map((r) => ({
        time: toUnix(r.date),
        value: r.volume,
        color: r.close >= r.open ? `${UP_COLOR}55` : `${DOWN_COLOR}55`,
      })),
    [rows],
  );
  const overlayData = useMemo(() => computeOverlays(rows), [rows]);

  // Create the chart once, tear it down on unmount.
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
      handleScale: { axisPressedMouseMove: true },
    });

    const candles = chart.addCandlestickSeries({
      upColor: UP_COLOR,
      downColor: DOWN_COLOR,
      borderUpColor: UP_COLOR,
      borderDownColor: DOWN_COLOR,
      wickUpColor: UP_COLOR,
      wickDownColor: DOWN_COLOR,
    });
    // Leave ~28% at the bottom for the volume histogram.
    candles.priceScale().applyOptions({
      scaleMargins: { top: 0.05, bottom: 0.28 },
    });

    const volume = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '', // overlay scale, independent of price axis
      color: `${UP_COLOR}55`,
    });
    volume.priceScale().applyOptions({
      scaleMargins: { top: 0.78, bottom: 0 },
    });

    chartRef.current = chart;
    candlesRef.current = candles;
    volumeRef.current = volume;

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
      candlesRef.current = null;
      volumeRef.current = null;
      overlayRefs.current = {};
    };
  }, [height, resolvedTheme]);

  // Push candle + volume data whenever it changes.
  useEffect(() => {
    candlesRef.current?.setData(candleData);
    volumeRef.current?.setData(volumeData);
    if (candleData.length > 0) chartRef.current?.timeScale().fitContent();
  }, [candleData, volumeData]);

  // Sync overlay series with requested overlays.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    for (const spec of OVERLAY_SPECS) {
      const wanted = overlays[spec.key] ?? false;
      const existing = overlayRefs.current[spec.key];
      if (wanted && !existing) {
        const series = chart.addLineSeries({
          color: OVERLAY_COLORS[spec.key],
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        series.setData(overlayData[spec.key]);
        overlayRefs.current[spec.key] = series;
      } else if (!wanted && existing) {
        chart.removeSeries(existing);
        delete overlayRefs.current[spec.key];
      } else if (wanted && existing) {
        existing.setData(overlayData[spec.key]);
      }
    }
  }, [overlays, overlayData]);

  return <div ref={containerRef} className={cn('w-full', className)} style={{ height }} />;
}

export function PriceChartLegend({
  overlays,
  onToggle,
}: {
  overlays: Partial<Record<OverlayKey, boolean>>;
  onToggle: (key: OverlayKey) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {OVERLAY_SPECS.map((spec) => {
        const active = overlays[spec.key] ?? false;
        const color = OVERLAY_COLORS[spec.key];
        return (
          <button
            key={spec.key}
            type="button"
            onClick={() => onToggle(spec.key)}
            aria-pressed={active}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors',
              active
                ? 'border-primary/40 bg-primary/5 text-foreground'
                : 'border-border bg-background text-muted-foreground hover:text-foreground',
            )}
          >
            <span
              aria-hidden
              className="size-2 rounded-full"
              style={{ backgroundColor: color }}
            />
            {labelFor(spec.key)}
          </button>
        );
      })}
    </div>
  );
}

// ——— helpers ———

function labelFor(key: OverlayKey): string {
  switch (key) {
    case 'sma20':
      return 'SMA 20';
    case 'sma50':
      return 'SMA 50';
    case 'sma200':
      return 'SMA 200';
    case 'ema12':
      return 'EMA 12';
    case 'ema26':
      return 'EMA 26';
  }
}

function toUnix(iso: string): Time {
  // Backend sends a date string "YYYY-MM-DD". Interpret as UTC to avoid TZ drift.
  const ts = Math.floor(new Date(`${iso}T00:00:00Z`).getTime() / 1000);
  return ts as UTCTimestamp;
}

function sma(values: number[], period: number): Array<number | null> {
  const out: Array<number | null> = [];
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i]!;
    if (i >= period) sum -= values[i - period]!;
    out.push(i >= period - 1 ? sum / period : null);
  }
  return out;
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

function computeOverlays(rows: OHLCVRow[]): Record<OverlayKey, LineData[]> {
  const closes = rows.map((r) => r.close);
  const times = rows.map((r) => toUnix(r.date));
  const series: Record<OverlayKey, LineData[]> = {
    sma20: [],
    sma50: [],
    sma200: [],
    ema12: [],
    ema26: [],
  };
  const pairs: Array<{ key: OverlayKey; values: Array<number | null> }> = [
    { key: 'sma20', values: sma(closes, 20) },
    { key: 'sma50', values: sma(closes, 50) },
    { key: 'sma200', values: sma(closes, 200) },
    { key: 'ema12', values: ema(closes, 12) },
    { key: 'ema26', values: ema(closes, 26) },
  ];
  for (const { key, values } of pairs) {
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (v != null) series[key].push({ time: times[i]!, value: v });
    }
  }
  return series;
}
