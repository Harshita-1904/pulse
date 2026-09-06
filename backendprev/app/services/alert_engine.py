from dataclasses import dataclass


@dataclass
class PulseAlert:
    symbol: str
    severity: str
    direction: str
    change_pct: float
    change_score: float
    message: str


def generate_alert(change: dict) -> PulseAlert | None:
    score = float(change.get("change_score") or 0)
    change_pct = float(
        change.get("price_change_since_last_seen") or 0
    )

    if score < 0.60:
        return None

    if change_pct > 0:
        direction = "positive"
        emoji = "🟢"
    elif change_pct < 0:
        direction = "negative"
        emoji = "🔴"
    else:
        direction = "neutral"
        emoji = "🟡"

    severity = change.get("severity", "significant")

    message = (
        f"{emoji} {change['symbol']} moved "
        f"{abs(change_pct):.2f}% since you last checked."
    )

    return PulseAlert(
        symbol=change["symbol"],
        severity=severity,
        direction=direction,
        change_pct=change_pct,
        change_score=score,
        message=message,
    )