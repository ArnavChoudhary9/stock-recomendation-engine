// Central list of backend endpoints. Keep in sync with src/api/routers/*.

export const API_PREFIX = '/api/v1';

export const endpoints = {
  health: `${API_PREFIX}/health`,
  config: `${API_PREFIX}/config`,
  pipelineRun: `${API_PREFIX}/pipeline/run`,

  stocks: `${API_PREFIX}/stocks`,
  stock: (symbol: string) => `${API_PREFIX}/stocks/${encodeURIComponent(symbol)}`,
  stockOhlcv: (symbol: string) => `${API_PREFIX}/stocks/${encodeURIComponent(symbol)}/ohlcv`,
  stockRefresh: (symbol: string) => `${API_PREFIX}/stocks/${encodeURIComponent(symbol)}/refresh`,

  stockAnalysis: (symbol: string) =>
    `${API_PREFIX}/stocks/${encodeURIComponent(symbol)}/analysis`,
  recommendations: `${API_PREFIX}/recommendations`,
  recommendationsHistory: `${API_PREFIX}/recommendations/history`,

  stockNews: (symbol: string) => `${API_PREFIX}/stocks/${encodeURIComponent(symbol)}/news`,

  stockReport: (symbol: string) => `${API_PREFIX}/stocks/${encodeURIComponent(symbol)}/report`,

  // Portfolio / Kite (return 501 until Phase 4B; UI renders coming-soon states)
  portfolioOverview: `${API_PREFIX}/portfolio/overview`,
  portfolioHoldings: `${API_PREFIX}/portfolio/holdings`,
  portfolioPositions: `${API_PREFIX}/portfolio/positions`,
  portfolioPerformance: `${API_PREFIX}/portfolio/performance`,
  portfolioAlerts: `${API_PREFIX}/portfolio/alerts`,
  portfolioAlert: (id: string) =>
    `${API_PREFIX}/portfolio/alerts/${encodeURIComponent(id)}`,
  kiteAuthUrl: `${API_PREFIX}/kite/auth-url`,
  kiteStatus: `${API_PREFIX}/kite/status`,
  kiteCallback: `${API_PREFIX}/kite/callback`,

  // Chat (Phase 6.7 — backend endpoint not yet implemented; UI handles 404/501)
  chatStream: `${API_PREFIX}/chat/stream`,
} as const;
