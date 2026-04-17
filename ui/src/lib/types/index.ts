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

export type MACDCrossover = 'bullish' | 'bearish';

export interface MACDFeatures {
  macd_line: number;
  signal_line: number;
  histogram: number;
  crossover: MACDCrossover | null;
  crossover_days_ago: number | null;
}

export interface BollingerBands {
  upper: number;
  middle: number;
  lower: number;
  percent_b: number;
  bandwidth: number;
  squeeze: boolean;
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
  macd: MACDFeatures | null;
  bollinger: BollingerBands | null;
}

export interface SubScores {
  moving_average: number;
  momentum: number;
  volume: number;
  volatility: number;
  fundamental: number;
  support_resistance: number;
  trend_following: number;
  mean_reversion: number;
}

export interface ScoringWeights {
  moving_average: number;
  momentum: number;
  volume: number;
  volatility: number;
  fundamental: number;
  support_resistance: number;
  trend_following: number;
  mean_reversion: number;
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

export type SentimentLabel = 'positive' | 'negative' | 'neutral';

export interface SentimentResult {
  score: number; // -1..+1
  label: SentimentLabel;
  confidence: number; // 0..1
  analyzer: string;
}

export interface Article {
  title: string;
  summary: string | null;
  url: string;
  source: string;
  published_at: string;
  sentiment: SentimentResult;
}

export interface NewsBundle {
  symbol: string;
  timestamp: string;
  articles: Article[];
  aggregate_sentiment: number; // -1..+1
  article_count: number;
  time_window_hours: number;
}

// ——— LLM reports ———

export interface NewsReference {
  title: string;
  url: string;
  source: string;
  published_at: string;
  sentiment_score: number;
  sentiment_label: string;
}

export interface StockReport {
  symbol: string;
  timestamp: string;
  summary: string;
  insights: string[];
  risks: string[];
  news_impact: string;
  confidence: number;
  reasoning_chain: string[];
  recommendation: Recommendation;
  recommendation_rationale: string;
  sources: NewsReference[];
  model_used: string | null;
  degraded: boolean;
}

// ——— Pipeline ———

export interface PipelineRunResult {
  scheduled: boolean;
  symbols_count: number;
  message: string;
}

// ——— Watchlist ———

export interface WatchlistItem {
  symbol: string;
  added_at: string;
  notes: string | null;
}

export interface AddToWatchlistRequest {
  symbol: string;
  notes?: string | null;
}

// ——— Stocks backfill ———

export interface BackfillRequest {
  symbols: string[];
  start_date?: string | null; // ISO YYYY-MM-DD
  days?: number | null;
  force?: boolean;
}

export interface BackfillResult {
  written: Record<string, number>;
  total_bars: number;
  failed: string[];
}

// ——— Portfolio (Phase 4B — endpoints return 501 until then) ———

export interface Holding {
  symbol: string;
  exchange: string;
  quantity: number;
  average_price: number;
  last_price: number;
  pnl: number;
  pnl_pct: number;
  day_change: number;
  day_change_pct: number;
}

export type Product = 'CNC' | 'MIS' | 'NRML' | 'CO' | 'BO';

export interface Position {
  symbol: string;
  exchange: string;
  product: Product;
  quantity: number;
  average_price: number;
  last_price: number;
  pnl: number;
  buy_quantity: number;
  sell_quantity: number;
}

export interface PortfolioOverview {
  total_investment: number;
  current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  day_pnl: number;
  holdings: Holding[];
  positions: Position[];
  allocation_by_sector: Record<string, number>;
  allocation_by_market_cap: Record<string, number>;
  concentration_warnings: string[];
  score_overlay: Record<string, number>;
  stale: boolean;
  as_of: string;
}

export type AlertType = 'score_drop' | 'signal_change' | 'volume_spike' | 'sentiment' | 'price';

export interface AlertRule {
  id: string;
  type: AlertType;
  symbol: string | null;
  threshold: number;
  enabled: boolean;
  created_at: string;
}

export interface Alert {
  id: string;
  rule_id: string;
  symbol: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
}

// ——— Kite session status ———

export interface KiteStatus {
  connected: boolean;
  expires_at: string | null;
  user_id: string | null;
}

// ——— Chat (Phase 6.7 — backend endpoint not yet implemented) ———

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  context_symbols?: string[];
  error?: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}
