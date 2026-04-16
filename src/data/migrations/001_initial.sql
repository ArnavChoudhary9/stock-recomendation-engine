-- Phase 1 initial schema
CREATE TABLE IF NOT EXISTS stocks (
    symbol      TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    sector      TEXT,
    industry    TEXT,
    exchange    TEXT DEFAULT 'NSE',
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ohlcv (
    symbol  TEXT NOT NULL,
    date    TEXT NOT NULL,
    open    REAL NOT NULL,
    high    REAL NOT NULL,
    low     REAL NOT NULL,
    close   REAL NOT NULL,
    volume  INTEGER NOT NULL,
    PRIMARY KEY (symbol, date),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE TABLE IF NOT EXISTS fundamentals (
    symbol      TEXT NOT NULL,
    date        TEXT NOT NULL,
    pe          REAL,
    market_cap  REAL,
    roe         REAL,
    eps         REAL,
    debt_equity REAL,
    promoter_holding REAL,
    dividend_yield   REAL,
    PRIMARY KEY (symbol, date),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON ohlcv(date);
CREATE INDEX IF NOT EXISTS idx_fundamentals_date ON fundamentals(date);

-- Phase 4B portfolio tables
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    date        TEXT NOT NULL,
    total_value REAL NOT NULL,
    invested    REAL NOT NULL,
    holdings    INTEGER NOT NULL,
    PRIMARY KEY (date)
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    symbol      TEXT,
    threshold   REAL NOT NULL,
    enabled     INTEGER DEFAULT 1,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id          TEXT PRIMARY KEY,
    rule_id     TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    message     TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    acknowledged INTEGER DEFAULT 0,
    FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
);
