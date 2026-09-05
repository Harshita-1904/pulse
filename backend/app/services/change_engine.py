"""Compute explainable, user-specific stock changes from persisted observations."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import sqrt
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.market import MarketData, PriceHistory, Stock
from app.models.watchlist import UserStockState


class ChangeIntelligenceError(Exception):
    """Raised when a requested stock does not exist or cannot be baselined."""


@dataclass(frozen=True)
class ChangeSummary:
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


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def get_stock(database: Session, symbol: str) -> Stock:
    stock = database.scalar(select(Stock).where(Stock.symbol == normalize_symbol(symbol)))
    if stock is None:
        raise ChangeIntelligenceError("Stock has not been collected yet")
    return stock


def get_latest_observation(database: Session, stock_id: int) -> MarketData | None:
    return database.scalar(select(MarketData).where(MarketData.stock_id == stock_id).order_by(MarketData.captured_at.desc()).limit(1))


def get_state(database: Session, user_id: str, stock_id: int) -> UserStockState | None:
    return database.scalar(select(UserStockState).where(UserStockState.user_id == user_id, UserStockState.stock_id == stock_id))


def percentage_change(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline is None or baseline == 0:
        return None
    return (current - baseline) / baseline * 100


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def standard_deviation(values: list[float]) -> float:
    return sqrt(sum((value - mean(values)) ** 2 for value in values) / len(values)) if len(values) > 1 else 0.0


def data_status_for(observation: MarketData) -> Literal["fresh", "stale"]:
    return "stale" if datetime.now(UTC) - observation.captured_at > timedelta(seconds=get_settings().market_data_max_age_seconds) else "fresh"


def unavailable_summary(stock: Stock, state: UserStockState | None) -> ChangeSummary:
    return ChangeSummary(stock.symbol, state.last_seen_at if state else None, None, None, state.last_seen_price if state else None, state.last_seen_volume if state else None, None, None, None, None, "first_view", False, None, None, None, None, "unavailable", "unavailable", "unavailable", ["No market quote has been collected for this stock yet."], "Market data is unavailable; refresh this stock before comparing it.", "unavailable", "No market data has been collected for this stock.")


def calculate_change(database: Session, user_id: str, symbol: str) -> ChangeSummary:
    stock = get_stock(database, symbol)
    state = get_state(database, user_id, stock.id)
    latest = get_latest_observation(database, stock.id)
    if latest is None:
        return unavailable_summary(stock, state)
    status = data_status_for(latest)
    if state is None or state.last_seen_price is None or state.last_seen_at is None:
        return ChangeSummary(stock.symbol, None, latest.price, latest.volume, None, None, None, None, None, None, "first_view", True, latest.captured_at, None, None, None, "new", "cold_start_fixed_threshold", "low", ["This stock has no previous viewing baseline."], "New to your watchlist — this price is now the comparison baseline.", status)

    price_delta = latest.price - state.last_seen_price
    price_percent = percentage_change(latest.price, state.last_seen_price)
    volume_delta = latest.volume - state.last_seen_volume if latest.volume is not None and state.last_seen_volume is not None else None
    volume_percent = percentage_change(latest.volume, state.last_seen_volume)
    direction: Literal["up", "down", "unchanged", "first_view"] = "up" if price_delta > 0 else "down" if price_delta < 0 else "unchanged"
    history = list(database.scalars(select(PriceHistory).where(PriceHistory.stock_id == stock.id).order_by(PriceHistory.recorded_at.asc()).limit(100)))
    returns = [percentage_change(history[i].price, history[i - 1].price) or 0.0 for i in range(1, len(history))]
    prior_prices = [point.price for point in history[:-1]]
    daily_change = percentage_change(latest.price, prior_prices[-1]) if prior_prices else None
    historical_ready = len(history) >= 5 and len(returns) >= 4
    if historical_ready and price_percent is not None and standard_deviation(returns) > 0:
        price_signal, method = min(abs((price_percent - mean(returns)) / standard_deviation(returns)) / 3, 1), "historical_z_score"
    else:
        price_signal, method = min(abs(price_percent or 0) / 5, 1), "cold_start_fixed_threshold"
    volumes = [point.volume for point in history[:-1] if point.volume is not None and point.volume > 0]
    volume_ratio = latest.volume / mean(volumes) if latest.volume is not None and volumes else None
    volume_signal = min(max((volume_ratio - 1) / 2, 0), 1) if volume_ratio is not None else None
    normal_volatility = standard_deviation(returns)
    volatility_signal = min(max((abs(daily_change) / normal_volatility - 1) / 2, 0), 1) if historical_ready and normal_volatility > 0 and daily_change is not None else None
    signals = [(0.5, price_signal)] + ([(0.3, volume_signal)] if volume_signal is not None else []) + ([(0.2, volatility_signal)] if volatility_signal is not None else [])
    score = sum(weight * signal for weight, signal in signals) / sum(weight for weight, _ in signals)
    severity: Literal["minor", "notable", "significant"] = "minor" if score < .30 else "notable" if score < .60 else "significant"
    complete = volume_signal is not None and volatility_signal is not None
    confidence: Literal["low", "medium", "high"] = "high" if len(history) >= 30 and complete else "medium" if historical_ready else "low"
    reasons = [f"Price {'increased' if price_delta > 0 else 'decreased' if price_delta < 0 else 'was unchanged'} {abs(price_percent or 0):.2f}% since you last checked."]
    if volume_ratio is not None:
        reasons.append(f"Trading volume is {volume_ratio:.1f}x its recorded average.")
    reasons.append("The move was compared with recorded historical price movements." if method == "historical_z_score" else "Limited history: fixed thresholds were used for this score.")
    return ChangeSummary(stock.symbol, state.last_seen_at, latest.price, latest.volume, state.last_seen_price, state.last_seen_volume, price_delta, price_percent, volume_delta, volume_percent, direction, latest.captured_at > state.last_seen_at, latest.captured_at, daily_change, volume_ratio, score, severity, method, confidence, reasons, f"{severity.capitalize()} {'positive' if direction == 'up' else 'negative' if direction == 'down' else 'neutral'} movement.", status)


def mark_seen(database: Session, user_id: str, symbol: str) -> UserStockState:
    stock = get_stock(database, symbol)
    latest = get_latest_observation(database, stock.id)
    if latest is None:
        raise ChangeIntelligenceError("No market data has been collected for this stock")
    state = get_state(database, user_id, stock.id)
    if state is None:
        state = UserStockState(user_id=user_id, stock_id=stock.id)
        database.add(state)
    state.last_seen_at, state.last_seen_price, state.last_seen_volume = datetime.now(UTC), latest.price, latest.volume
    database.commit()
    database.refresh(state)
    return state
