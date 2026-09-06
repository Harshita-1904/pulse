"""Twelve Data integration for current and historical market data."""

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.config import get_settings


class TwelveDataError(Exception):
    """Raised when Twelve Data cannot provide usable market data."""


@dataclass(frozen=True)
class TwelveQuote:
    symbol: str
    price: float
    volume: float | None
    provider_timestamp: datetime | None


@dataclass(frozen=True)
class TwelveHistoricalPoint:
    timestamp: datetime
    price: float
    volume: float | None


def _request(endpoint: str, params: dict) -> dict:
    settings = get_settings()
    if not settings.twelve_data_api_key:
        raise TwelveDataError("TWELVE_DATA_API_KEY is not configured")

    request_params = {**params, "apikey": settings.twelve_data_api_key}
    try:
        response = httpx.get(
            f"{settings.twelve_data_base_url.rstrip('/')}/{endpoint.lstrip('/')}",
            params=request_params,
            timeout=settings.twelve_data_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise TwelveDataError(f"Twelve Data request failed: {error}") from error

    if isinstance(payload, dict) and payload.get("status") == "error":
        raise TwelveDataError(str(payload.get("message") or "Twelve Data returned an error"))
    return payload


def _parse_timestamp(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(int(value), tz=UTC)
        text = str(value).strip()
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def get_quote(symbol: str, exchange: str | None = None) -> TwelveQuote:
    params = {
    "symbol": symbol.strip().upper(),
    "interval": interval,
    "outputsize": max(1, min(outputsize, 5000)),
    "exchange": (exchange or "NSE").strip().upper(),
}
    payload = _request("quote", params)
    try:
        price = float(payload["close"])
        raw_volume = payload.get("volume")
        volume = float(raw_volume) if raw_volume not in (None, "") else None
    except (KeyError, TypeError, ValueError) as error:
        raise TwelveDataError("Twelve Data returned an invalid quote") from error

    timestamp = _parse_timestamp(payload.get("timestamp") or payload.get("datetime"))
    return TwelveQuote(
        symbol=symbol.strip().upper(),
        price=price,
        volume=volume,
        provider_timestamp=timestamp,
    )


def get_historical_prices(
    symbol: str,
    exchange: str | None = None,
    interval: str = "1day",
    outputsize: int = 100,
) -> list[TwelveHistoricalPoint]:
    params = {
    "symbol": symbol.strip().upper(),
    "interval": interval,
    "outputsize": max(1, min(outputsize, 5000)),
    "exchange": (exchange or "NSE").strip().upper(),
}

    payload = _request("time_series", params)
    values = payload.get("values") if isinstance(payload, dict) else None
    if not isinstance(values, list):
        raise TwelveDataError("Twelve Data did not return historical values")

    points: list[TwelveHistoricalPoint] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        timestamp = _parse_timestamp(item.get("datetime"))
        try:
            price = float(item["close"])
            raw_volume = item.get("volume")
            volume = float(raw_volume) if raw_volume not in (None, "") else None
        except (KeyError, TypeError, ValueError):
            continue
        if timestamp is None:
            continue
        points.append(TwelveHistoricalPoint(timestamp, price, volume))

    points.sort(key=lambda point: point.timestamp)
    return points
