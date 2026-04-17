// TypeScript mirrors of src/contracts/*.py. Keep in lockstep with the backend.
// When the Pydantic contracts change, update here too.

// ——— API envelopes ———

export interface ResponseMeta {
  timestamp: string;
  version: string;
  request_id?: string | null;
}

export interface APIResponse<T> {
  data: T;
  meta: ResponseMeta;
}

export interface PaginationMeta {
  total: number;
  limit: number;
  offset: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: PaginationMeta;
  meta: ResponseMeta;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
}

export interface APIErrorEnvelope {
  error: ErrorDetail;
  meta: ResponseMeta;
}

// ——— System ———

export type HealthLevel = 'ok' | 'degraded' | 'down';

export interface HealthStatus {
  status: HealthLevel;
  components: Record<string, string>;
  uptime_seconds: number;
}

// ——— Data ———

export type Exchange = 'NSE' | 'BSE';

export interface OHLCVRow {
  symbol: string;
  date: string; // ISO date
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Fundamentals {
  symbol: string;
  date: string;
  pe: number | null;
  market_cap: number | null;
  roe: number | null;
  eps: number | null;
  debt_equity: number | null;
  promoter_holding: number | null;
  dividend_yield: number | null;
}

export interface StockInfo {
  symbol: string;
  name: string;
  sector: string | null;
  industry: string | null;
  exchange: Exchange;
  updated_at: string;
}

export interface StockDetail {
  info: StockInfo;
  fundamentals: Fundamentals | null;
  latest_close: number | null;
  latest_date: string | null;
}

// ——— Processing / Analysis ———

export type Alignment = 'bullish' | 'bearish' | 'mixed';
export type Slope = 'rising' | 'falling' | 'flat';
export type Crossover = 'golden_cross' | 'death_cross';
export type MarketCapTier = 'large' | 'mid' | 'small' | 'micro';
export type Recommendation = 'BUY' | 'HOLD' | 'SELL';

export interface MovingAverages {
  sma_20: number;
  sma_50: number;
  sma_200: number;
  ema_12: number;
  ema_26: number;
  price_to_sma20_pct: number;
  price_to_sma50_pct: number;
  price_to_sma200_pct: number;
  alignment: Alignment;
  sma50_slope: Slope;
  sma200_slope: Slope;
  crossover: Crossover | null;
  crossover_days_ago: number | null;
}

export interface Momentum {
  rsi_14: number;
  return_5d: number;
  return_10d: number;
  return_20d: number;
}

export interface VolumeFeatures {
  current_volume: number;
  avg_volume_20d: number;
  volume_ratio: number;
  obv: number;
}

export interface Volatility {
  atr_14: number;
  std_dev_20: number;
}

export interface FundamentalFeatures {
  pe: number | null;
  pe_vs_sector_median: number | null;
  market_cap: number | null;
  market_cap_tier: MarketCapTier | null;
  roe: number | null;
  roe_sector_rank: number | null;
}

export interface SupportResistance {
  high_52w: number;
  low_52w: number;
  distance_to_52w_high_pct: number;
  distance_to_52w_low_pct: number;
  near_52w_high: boolean;
  near_52w_low: boolean;
}

export interface Features {
  symbol: string;
  as_of: string;
  last_close: number;
  moving_averages: MovingAverages;
  momentum: Momentum;
  volume: VolumeFeatures;
  volatility: Volatility;
  fundamentals: FundamentalFeatures;
  support_resistance: SupportResistance;
}

export interface SubScores {
  moving_average: number;
  momentum: number;
  volume: number;
  volatility: number;
  fundamental: number;
  support_resistance: number;
}

export interface AnalysisMetadata {
  config_hash: string;
  scoring_version: string;
  computed_at: string;
  data_points_used: number;
  warnings: string[];
}

export interface StockAnalysis {
  symbol: string;
  timestamp: string;
  moving_averages: MovingAverages;
  features: Features;
  score: number;
  sub_scores: SubScores;
  signals: Record<string, boolean | string>;
  metadata: AnalysisMetadata;
  recommendation: Recommendation;
  recommendation_rationale: string;
}

// ——— News ———

export interface Article {
  title: string;
  summary: string | null;
  source: string;
  url: string;
  published_at: string;
  sentiment: number | null;
}

export interface NewsBundle {
  symbol: string;
  timestamp: string;
  articles: Article[];
  aggregate_sentiment: number;
  article_count: number;
  time_window_hours: number;
}

// ——— LLM reports ———

export interface StockReport {
  symbol: string;
  timestamp: string;
  summary: string;
  insights: string[];
  risks: string[];
  news_impact: string;
  confidence: number;
  reasoning_chain: string[];
}

// ——— Pipeline ———

export interface PipelineRunResult {
  scheduled: boolean;
  symbols_count: number;
  message: string;
}
