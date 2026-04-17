// Indicator reference — single source of truth for inline tooltips and
// the Help page. Keys use the same identifiers as the backend contracts
// and sub-score labels.

export interface IndicatorEntry {
  key: string;
  label: string;
  short: string;
  category: 'moving_average' | 'momentum' | 'volume' | 'volatility' | 'support_resistance' | 'composite';
  summary: string;
  detail: string;
  interpretation?: string;
}

export const INDICATORS: Record<string, IndicatorEntry> = {
  sma: {
    key: 'sma',
    label: 'Simple Moving Average (SMA)',
    short: 'SMA',
    category: 'moving_average',
    summary: 'Average closing price over the last N bars.',
    detail:
      'Smooths short-term noise and highlights the trend. Shorter windows (20) react faster; longer windows (200) show the primary trend.',
    interpretation:
      'Price above SMA → uptrend. Price crossing below → weakening. SMA(20) above SMA(50) above SMA(200) is a bullish stack.',
  },
  ema: {
    key: 'ema',
    label: 'Exponential Moving Average (EMA)',
    short: 'EMA',
    category: 'moving_average',
    summary: 'Weighted moving average that reacts faster to recent prices.',
    detail:
      'Weights recent bars more heavily than old ones. EMA(12) and EMA(26) are the inputs to the MACD.',
    interpretation:
      'EMA turning up before the SMA is an early momentum signal. Watch EMA crosses with care in choppy markets.',
  },
  ma_alignment: {
    key: 'ma_alignment',
    label: 'MA alignment',
    short: 'Alignment',
    category: 'moving_average',
    summary: 'How the three SMAs are stacked relative to each other.',
    detail:
      'Bullish = SMA20 > SMA50 > SMA200. Bearish = SMA20 < SMA50 < SMA200. Mixed = any other ordering, usually a transition or range.',
    interpretation:
      'Bullish alignment is a regime signal: durable trends tend to preserve it for weeks. Mixed alignment is a caution sign.',
  },
  golden_cross: {
    key: 'golden_cross',
    label: 'Golden cross',
    short: 'Golden cross',
    category: 'moving_average',
    summary: 'SMA(50) crossing above SMA(200) — a classic bullish trend signal.',
    detail:
      'Tracked for a configurable lookback window (default 5 days). Shown with "Nd ago" so you know how fresh the cross is.',
    interpretation: 'Stronger when volume expands on the cross and the SMA(200) slope is flat or rising.',
  },
  death_cross: {
    key: 'death_cross',
    label: 'Death cross',
    short: 'Death cross',
    category: 'moving_average',
    summary: 'SMA(50) crossing below SMA(200) — bearish trend signal.',
    detail: 'Mirror of the golden cross. Frequently marks the start of a longer-term downtrend.',
    interpretation: 'Weight more heavily when the 200-day slope is already flattening or turning down.',
  },
  rsi: {
    key: 'rsi',
    label: 'RSI (14)',
    short: 'RSI',
    category: 'momentum',
    summary: 'Relative Strength Index — a 0–100 momentum oscillator over 14 bars.',
    detail:
      'Compares average up-days to average down-days. Above 70 is often called overbought, below 30 oversold.',
    interpretation:
      'In uptrends, RSI can sit above 50 for long stretches — don\'t short a strong trend on RSI alone. Divergences (price up, RSI down) are the higher-quality signal.',
  },
  returns: {
    key: 'returns',
    label: 'Returns (5d / 10d / 20d)',
    short: 'Returns',
    category: 'momentum',
    summary: 'Rolling percentage change over the last 5, 10, and 20 trading days.',
    detail: 'A coarse read on trend strength at different horizons.',
    interpretation: 'Positive across all three horizons = sustained upward drift. Sign flips between horizons hint at reversals.',
  },
  volume_ratio: {
    key: 'volume_ratio',
    label: 'Volume ratio',
    short: 'Vol ratio',
    category: 'volume',
    summary: 'Today\'s volume divided by the 20-day average volume.',
    detail: 'Values above 2× are considered volume spikes; below 0.5× are unusually quiet.',
    interpretation:
      'A spike with a price advance confirms the move. A spike with falling price can mark capitulation or distribution.',
  },
  obv: {
    key: 'obv',
    label: 'On-Balance Volume (OBV)',
    short: 'OBV',
    category: 'volume',
    summary: 'Cumulative running total of volume, signed by the day\'s price direction.',
    detail: 'Adds the day\'s volume when price closes up, subtracts it when price closes down.',
    interpretation:
      'Look for OBV divergence vs price: if OBV is falling while price makes new highs, demand is weakening.',
  },
  atr: {
    key: 'atr',
    label: 'Average True Range (ATR-14)',
    short: 'ATR',
    category: 'volatility',
    summary: 'Average daily trading range over 14 bars — a raw volatility number in price units.',
    detail: 'Measures how much the stock typically moves day-to-day. Higher ATR = wider swings.',
    interpretation: 'Useful for sizing stops — many practitioners place stops at 1.5× to 3× ATR below the entry.',
  },
  stddev: {
    key: 'stddev',
    label: 'Std deviation (σ, 20d)',
    short: 'σ',
    category: 'volatility',
    summary: '20-day standard deviation of daily closes — a statistical volatility measure.',
    detail: 'Also the input used to construct Bollinger Bands (mid-band ± 2σ).',
    interpretation: 'Rising σ with a range-bound price often precedes a breakout. Low σ after a trend = consolidation.',
  },
  macd: {
    key: 'macd',
    label: 'MACD (12, 26, 9)',
    short: 'MACD',
    category: 'momentum',
    summary: 'Moving Average Convergence Divergence — an EMA-based momentum indicator.',
    detail:
      'MACD line = EMA(12) − EMA(26). Signal line = EMA(9) of the MACD line. Histogram = MACD − Signal.',
    interpretation:
      'Bullish: MACD crossing above signal and/or histogram flipping positive. Watch for zero-line crosses as a stronger trend confirmation.',
  },
  bollinger: {
    key: 'bollinger',
    label: 'Bollinger Bands (20, 2σ)',
    short: 'BB',
    category: 'volatility',
    summary: 'Envelope of SMA(20) ± 2 standard deviations — contains most price action.',
    detail:
      'Middle band is the 20-day SMA. Upper/lower bands are 2σ above/below. %B locates price within the bands; bandwidth measures their width.',
    interpretation:
      'A narrow band ("squeeze") often precedes a volatility expansion. Tags of the outer bands in a trend are not automatically reversals.',
  },
  hl_52w: {
    key: 'hl_52w',
    label: '52-week high / low',
    short: '52w H/L',
    category: 'support_resistance',
    summary: 'Highest and lowest close in the trailing 52 weeks.',
    detail: 'Used for distance-to-high and distance-to-low percentages, and "near 52w high/low" flags.',
    interpretation:
      'Stocks pinned near 52w highs often continue higher (momentum persistence). Near 52w lows, look for capitulation volume before bottom-fishing.',
  },
  composite_score: {
    key: 'composite_score',
    label: 'Composite score',
    short: 'Score',
    category: 'composite',
    summary: 'Weighted average of the sub-scores, normalised to 0–100.',
    detail:
      'Weights come from `config/processing.yaml` and are shown on the score breakdown when loaded. Rows with zero weight are dimmed.',
    interpretation:
      'Treat the score as a ranking aid, not a buy/sell trigger on its own. Always check the signals + news + fundamentals.',
  },
  sub_moving_average: {
    key: 'sub_moving_average',
    label: 'MA sub-score',
    short: 'MA',
    category: 'composite',
    summary: 'How favourable the moving-average picture is: stacking, slopes, crossover recency, distance to price.',
    detail: 'Rewards bullish stacks and rising slopes; penalises bearish alignment and price far below SMA(200).',
  },
  sub_momentum: {
    key: 'sub_momentum',
    label: 'Momentum sub-score',
    short: 'Momentum',
    category: 'composite',
    summary: 'Combines RSI and recent returns (5d / 10d / 20d) into one number.',
    detail: 'Penalises extreme RSI and rewards sustained positive returns across horizons.',
  },
  sub_volume: {
    key: 'sub_volume',
    label: 'Volume sub-score',
    short: 'Volume',
    category: 'composite',
    summary: 'Reads volume ratio vs 20d average and OBV trend.',
    detail: 'Higher when volume confirms price direction; lower when volume dries up or diverges.',
  },
  sub_volatility: {
    key: 'sub_volatility',
    label: 'Volatility sub-score',
    short: 'Volatility',
    category: 'composite',
    summary: 'Prefers predictable, moderate volatility over extreme or vanishing volatility.',
    detail: 'Both ultra-low and ultra-high σ push this score toward zero.',
  },
  sub_fundamental: {
    key: 'sub_fundamental',
    label: 'Fundamental sub-score',
    short: 'Fundamental',
    category: 'composite',
    summary: 'PE vs sector median, ROE percentile, market-cap tier, promoter holding.',
    detail: 'Rewards reasonable valuation (PE near sector median) plus healthy ROE.',
  },
  sub_support_resistance: {
    key: 'sub_support_resistance',
    label: 'Support / Resistance sub-score',
    short: 'Support/Resist.',
    category: 'composite',
    summary: 'Position within the 52-week range.',
    detail: 'Near 52w high in a strong trend scores high; near 52w low with weak momentum scores low.',
  },
  sub_trend_following: {
    key: 'sub_trend_following',
    label: 'Trend (MACD) sub-score',
    short: 'Trend (MACD)',
    category: 'composite',
    summary: 'Derived from MACD histogram + crossovers.',
    detail: 'Positive histogram that is widening = strongest trend signal.',
  },
  sub_mean_reversion: {
    key: 'sub_mean_reversion',
    label: 'Mean reversion (BB) sub-score',
    short: 'Mean rev. (BB)',
    category: 'composite',
    summary: 'Uses %B and bandwidth — rewards reversion entries at band extremes.',
    detail: 'A squeeze that resolves into a band expansion also lifts this score.',
  },
};

export const INDICATOR_CATEGORIES: Array<{
  key: IndicatorEntry['category'];
  label: string;
  description: string;
}> = [
  {
    key: 'moving_average',
    label: 'Moving averages',
    description: 'Smoothed price — the backbone of trend analysis.',
  },
  {
    key: 'momentum',
    label: 'Momentum',
    description: 'How fast and in which direction price is moving.',
  },
  {
    key: 'volume',
    label: 'Volume',
    description: 'Confirmation (or denial) of price moves by participation.',
  },
  {
    key: 'volatility',
    label: 'Volatility',
    description: 'How much the stock swings — sets expectations for stop sizing and breakout probability.',
  },
  {
    key: 'support_resistance',
    label: 'Support / Resistance',
    description: 'Reference levels that tend to attract price.',
  },
  {
    key: 'composite',
    label: 'Composite score',
    description: 'How the sub-scores combine into one ranking number.',
  },
];
