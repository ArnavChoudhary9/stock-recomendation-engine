-- Phase 5 watchlist feature
CREATE TABLE IF NOT EXISTS watchlist (
    symbol      TEXT PRIMARY KEY,
    added_at    TEXT NOT NULL,
    notes       TEXT
);

CREATE INDEX IF NOT EXISTS idx_watchlist_added_at ON watchlist(added_at);
