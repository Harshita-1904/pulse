"""Request and response schemas for user-owned watchlists."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WatchlistCreateRequest(BaseModel):
    """Payload for a named user watchlist."""

    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class WatchlistStockRequest(BaseModel):
    """Stock to add to a watchlist."""

    symbol: str = Field(min_length=1, max_length=32)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not symbol or not all(character.isalnum() or character in ".-" for character in symbol):
            raise ValueError("Symbol may contain only letters, numbers, periods, and hyphens")
        return symbol


class WatchlistStockResponse(BaseModel):
    """A stock entry within a particular watchlist."""

    symbol: str
    name: str | None
    exchange: str | None
    added_at: datetime


class WatchlistResponse(BaseModel):
    """A watchlist with its current stock membership."""

    id: str
    name: str
    created_at: datetime
    stocks: list[WatchlistStockResponse]


class WatchlistStockMutationResponse(BaseModel):
    """Confirmation of a watchlist membership transition."""

    watchlist_id: str
    symbol: str
    state: str
