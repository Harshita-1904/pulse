"""Dashboard-level API responses composed from watchlist and change data."""

from pydantic import BaseModel

from app.schemas.changes import ChangeSummaryResponse


class WatchlistOverviewResponse(BaseModel):
    """One API response containing the current intelligence for a watchlist."""

    watchlist_id: str
    watchlist_name: str
    total_stocks: int
    changed_count: int
    up_count: int
    down_count: int
    unseen_count: int
    items: list[ChangeSummaryResponse]


class BatchRefreshItem(BaseModel):
    """Outcome of refreshing one watchlist symbol."""

    symbol: str
    status: str
    detail: str | None = None


class BatchRefreshResponse(BaseModel):
    """The independent outcome for every stock in a batch refresh."""

    watchlist_id: str
    refreshed_count: int
    failed_count: int
    items: list[BatchRefreshItem]
