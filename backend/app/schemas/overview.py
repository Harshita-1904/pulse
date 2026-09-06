"""Dashboard-level API responses composed from watchlist and change data."""

from pydantic import BaseModel
from app.schemas.changes import ChangeSummaryResponse


class MissedAlertResponse(BaseModel):
    symbol: str
    change_pct: float | None
    change_score: float | None
    severity: str
    direction: str
    message: str
    reasons: list[str]


class WatchlistOverviewResponse(BaseModel):
    watchlist_id: str
    watchlist_name: str
    total_stocks: int
    changed_count: int
    up_count: int
    down_count: int
    unseen_count: int
    missed_alerts: list[MissedAlertResponse]
    items: list[ChangeSummaryResponse]


class BatchRefreshItem(BaseModel):
    symbol: str
    status: str
    detail: str | None = None


class BatchRefreshResponse(BaseModel):
    watchlist_id: str
    refreshed_count: int
    failed_count: int
    items: list[BatchRefreshItem]
