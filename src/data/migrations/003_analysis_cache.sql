-- Phase 6 cache tables: persist deterministic analyses and LLM reports
-- keyed by a cache_key that encodes (latest OHLCV date, latest fundamentals
-- date, scoring config hash). A miss or mismatch triggers recomputation.

CREATE TABLE IF NOT EXISTS stock_analyses (
    symbol       TEXT PRIMARY KEY,
    cache_key    TEXT NOT NULL,
    payload      TEXT NOT NULL,
    computed_at  TEXT NOT NULL,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_stock_analyses_key ON stock_analyses(cache_key);

CREATE TABLE IF NOT EXISTS stock_reports (
    symbol       TEXT PRIMARY KEY,
    cache_key    TEXT NOT NULL,
    payload      TEXT NOT NULL,
    computed_at  TEXT NOT NULL,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_stock_reports_key ON stock_reports(cache_key);
