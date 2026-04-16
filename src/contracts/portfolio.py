"""Portfolio + Kite Connect contracts: holdings, positions, snapshots, alerts."""

from datetime import date as DateType
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Product = Literal["CNC", "MIS", "NRML", "CO", "BO"]
AlertType = Literal["score_drop", "signal_change", "volume_spike", "sentiment", "price"]


class Holding(BaseModel):
    """A long-term holding from the Kite portfolio."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    exchange: str
    quantity: int
    average_price: float = Field(..., ge=0)
    last_price: float = Field(..., ge=0)
    pnl: float
    pnl_pct: float
    day_change: float
    day_change_pct: float

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class Position(BaseModel):
    """An open position (intraday or delivery)."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    exchange: str
    product: Product
    quantity: int
    average_price: float = Field(..., ge=0)
    last_price: float = Field(..., ge=0)
    pnl: float
    buy_quantity: int = Field(..., ge=0)
    sell_quantity: int = Field(..., ge=0)

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()


class PortfolioOverview(BaseModel):
    """Composite portfolio view used by the dashboard."""

    model_config = ConfigDict(frozen=True)

    total_investment: float
    current_value: float
    total_pnl: float
    total_pnl_pct: float
    day_pnl: float
    holdings: list[Holding] = Field(default_factory=list)
    positions: list[Position] = Field(default_factory=list)
    allocation_by_sector: dict[str, float] = Field(
        default_factory=dict, description="Sector → fraction of portfolio (0-1)"
    )
    allocation_by_market_cap: dict[str, float] = Field(default_factory=dict)
    concentration_warnings: list[str] = Field(default_factory=list)
    score_overlay: dict[str, float] = Field(
        default_factory=dict, description="Symbol → analysis score in [0,1]"
    )
    stale: bool = Field(False, description="True when data is from cache because Kite is down")
    as_of: datetime


class PortfolioSnapshot(BaseModel):
    """Daily snapshot stored to compute time-series performance / XIRR."""

    model_config = ConfigDict(frozen=True)

    date: DateType
    total_value: float = Field(..., ge=0)
    invested_value: float = Field(..., ge=0)
    holdings_count: int = Field(..., ge=0)


class AlertRule(BaseModel):
    """User-configured rule that triggers Alerts."""

    id: str
    type: AlertType
    symbol: str | None = Field(None, description="None = applies to all holdings")
    threshold: float
    enabled: bool = True
    created_at: datetime

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else None


class Alert(BaseModel):
    """A fired alert awaiting acknowledgement."""

    id: str
    rule_id: str
    symbol: str
    message: str
    timestamp: datetime
    acknowledged: bool = False

    @field_validator("symbol")
    @classmethod
    def _upper_symbol(cls, v: str) -> str:
        return v.strip().upper()
