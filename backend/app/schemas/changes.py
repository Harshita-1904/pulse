"""Response schemas for change-intelligence endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ChangeSummaryResponse(BaseModel):
    """What has changed in a stock since the user last marked it as seen."""

    symbol: str
    last_seen_at: datetime | None
    current_price: float | None
    current_volume: float | None
    baseline_price: float | None
    baseline_volume: float | None
    price_change: float | None
    price_change_percent: float | None
    volume_change: float | None
    volume_change_percent: float | None
    direction: Literal["up", "down", "unchanged", "first_view"]
    has_new_data: bool
    latest_observed_at: datetime | None
    daily_change_percent: float | None
    volume_ratio: float | None
    change_score: float | None
    severity: Literal["minor", "notable", "significant", "new", "unavailable"]
    method: Literal["cold_start_fixed_threshold", "historical_z_score", "unavailable"]
    confidence: Literal["low", "medium", "high", "unavailable"]
    reasons: list[str]
    verdict: str
    data_status: Literal["fresh", "stale", "unavailable"]
    data_error: str | None = None


class MarkSeenResponse(BaseModel):
    """Confirmation that a user checkpoint was updated from the latest quote."""

    symbol: str
    last_seen_at: datetime
    baseline_price: float
    baseline_volume: float | None
