"""Data layer contracts: OHLCV, fundamentals, stock metadata, instruments."""

from datetime import date as DateType
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Exchange = Literal["NSE", "BSE"]


class OHLCVRow(BaseModel):
    """A single daily OHLCV bar for a stock."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(..., min_length=1, description="Trading symbol, e.g. RELIANCE")
    date: DateType = Field(..., description="Trading date (IST)")
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class Fundamentals(BaseModel):
    """Fundamental snapshot for a stock at a point in time."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(..., min_length=1)
    date: DateType
    pe: float | None = Field(default=None, description="Price-to-earnings ratio")
    market_cap: float | None = Field(default=None, ge=0, description="Market capitalisation in INR")
    roe: float | None = Field(default=None, description="Return on equity (fraction, e.g. 0.18)")
    eps: float | None = None
    debt_equity: float | None = Field(default=None, ge=0)
    promoter_holding: float | None = Field(default=None, ge=0, le=1, description="Fraction 0-1")
    dividend_yield: float | None = Field(default=None, ge=0, description="Fraction 0-1")

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class StockInfo(BaseModel):
    """Static metadata about a stock listed on NSE/BSE."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(..., min_length=1)
    name: str
    sector: str | None = None
    industry: str | None = None
    exchange: Exchange = "NSE"
    updated_at: datetime

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class Instrument(BaseModel):
    """Kite Connect instrument record (used by KiteClient.get_instruments)."""

    model_config = ConfigDict(frozen=True)

    instrument_token: int
    exchange_token: int | None = None
    tradingsymbol: str
    name: str | None = None
    exchange: str
    segment: str | None = None
    instrument_type: str | None = None
    tick_size: float | None = None
    lot_size: int | None = None
