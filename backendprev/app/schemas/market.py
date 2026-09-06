"""Request and response schemas for market-data endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StockCreateRequest(BaseModel):
    """Optional metadata for a stock that is added before its first quote refresh."""

    symbol: str = Field(min_length=1, max_length=32)
    name: str | None = Field(default=None, max_length=255)
    exchange: str | None = Field(default=None, max_length=64)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not symbol or not all(character.isalnum() or character in ".-" for character in symbol):
            raise ValueError("Symbol may contain only letters, numbers, periods, and hyphens")
        return symbol


class StockResponse(BaseModel):
    """A tracked market instrument."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    name: str | None
    exchange: str | None


class QuoteResponse(BaseModel):
    """A validated price observation and its freshness metadata."""

    symbol: str
    price: float
    volume: float | None
    source: str
    provider_timestamp: datetime | None
    captured_at: datetime
    is_cached: bool


class PriceHistoryPointResponse(BaseModel):
    """One persisted observation for a stock-detail price chart."""

    price: float
    volume: float | None
    recorded_at: datetime
