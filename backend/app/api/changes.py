"""Endpoints that explain what changed since a user last checked a stock."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DatabaseSession
from app.schemas.changes import ChangeSummaryResponse, MarkSeenResponse
from app.services.change_engine import (
    ChangeIntelligenceError,
    ChangeSummary,
    calculate_change,
    mark_seen,
)


router = APIRouter(prefix="/changes", tags=["changes"])


def to_response(summary: ChangeSummary) -> ChangeSummaryResponse:
    """Translate service output to a documented API response."""
    return ChangeSummaryResponse(**summary.__dict__)


@router.get("/{symbol}", response_model=ChangeSummaryResponse)
def get_changes(symbol: str, current_user: CurrentUser, database: DatabaseSession) -> ChangeSummaryResponse:
    """Show the market movement for one stock since this user last marked it seen."""
    try:
        return to_response(calculate_change(database, current_user.id, symbol))
    except ChangeIntelligenceError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{symbol}/mark-seen", response_model=MarkSeenResponse)
def mark_stock_seen(symbol: str, current_user: CurrentUser, database: DatabaseSession) -> MarkSeenResponse:
    """Set the latest stored quote as the baseline for future change calculations."""
    try:
        checkpoint = mark_seen(database, current_user.id, symbol)
    except ChangeIntelligenceError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return MarkSeenResponse(
        symbol=symbol.strip().upper(),
        last_seen_at=checkpoint.last_seen_at,
        baseline_price=checkpoint.last_seen_price,
        baseline_volume=checkpoint.last_seen_volume,
    )
