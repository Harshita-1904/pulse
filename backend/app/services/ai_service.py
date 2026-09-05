"""AI assistant orchestration for Pulse.

The service builds factual context from Pulse's deterministic change engine and
lets the LLM explain that context. The model is explicitly instructed not to
invent prices, percentages, scores, or events.
"""

from __future__ import annotations

import json
import re

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.change_engine import ChangeIntelligenceError, ChangeSummary, calculate_change
from app.services.state_manager import get_or_create_default_watchlist, get_user_watchlist


class AIServiceError(Exception):
    """Raised when the AI provider cannot produce an answer."""


def detect_intent(question: str) -> str:
    """Route a small, predictable set of Pulse intents."""
    text = question.lower()

    if any(phrase in text for phrase in ["what changed", "changed since", "since i last checked", "what happened"]):
        return "what_changed"
    if any(phrase in text for phrase in ["why is", "why are", "why did", "reason for"]):
        return "why_moved"
    if any(phrase in text for phrase in ["needs attention", "need my attention", "pay attention", "watch out"]):
        return "attention"
    if any(phrase in text for phrase in ["summarize", "summary", "overview", "my watchlist"]):
        return "watchlist_summary"
    if any(phrase in text for phrase in ["biggest", "most moved", "moved the most", "largest move"]):
        return "biggest_move"
    return "general"


def _candidate_symbols(question: str, available: list[str]) -> list[str]:
    """Find known watchlist/catalogue symbols mentioned in the question."""
    upper = question.upper()
    return [symbol for symbol in available if re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", upper)]


def _summary_to_dict(summary: ChangeSummary) -> dict:
    """Convert deterministic Pulse output into safe JSON context for the LLM."""
    return {
        "symbol": summary.symbol,
        "current_price": summary.current_price,
        "baseline_price": summary.baseline_price,
        "price_change_percent": summary.price_change_percent,
        "daily_change_percent": summary.daily_change_percent,
        "volume_ratio": summary.volume_ratio,
        "change_score": summary.change_score,
        "direction": summary.direction,
        "severity": summary.severity,
        "confidence": summary.confidence,
        "reasons": summary.reasons,
        "verdict": summary.verdict,
        "data_status": summary.data_status,
        "latest_observed_at": summary.latest_observed_at.isoformat() if summary.latest_observed_at else None,
        "last_seen_at": summary.last_seen_at.isoformat() if summary.last_seen_at else None,
        "data_error": summary.data_error,
    }


def collect_context(database: Session, user_id: str, question: str) -> tuple[str, list[str], list[dict]]:
    """Collect only factual, user-scoped context required to answer a question."""
    watchlist = get_or_create_default_watchlist(database, user_id)
    watchlist = get_user_watchlist(database, user_id, watchlist.id)
    available = sorted({entry.stock.symbol for entry in watchlist.entries})
    intent = detect_intent(question)
    mentioned = _candidate_symbols(question, available)

    if mentioned:
        symbols = mentioned
    elif intent in {"why_moved", "what_changed"}:
        symbols = available
    else:
        symbols = available

    summaries: list[dict] = []
    for symbol in symbols:
        try:
            summaries.append(_summary_to_dict(calculate_change(database, user_id, symbol)))
        except ChangeIntelligenceError:
            continue

    if intent == "biggest_move":
        summaries.sort(key=lambda item: abs(item.get("price_change_percent") or 0), reverse=True)
        summaries = summaries[:3]
    elif intent == "attention":
        summaries.sort(
            key=lambda item: (
                item.get("severity") == "significant",
                item.get("change_score") or 0,
                abs(item.get("price_change_percent") or 0),
            ),
            reverse=True,
        )
        summaries = summaries[:5]

    return intent, symbols, summaries


def build_system_prompt() -> str:
    """Return a strict grounding prompt for the LLM."""
    return (
        "You are Pulse, an AI assistant inside a smart market watchlist. "
        "Explain only the facts supplied in the JSON context. Never invent or estimate "
        "prices, percentages, dates, market events, news, causes, or scores. "
        "Do not override the supplied direction, severity, confidence, or reasons. "
        "When data_status is stale or unavailable, say so clearly. "
        "Do not present financial advice or tell the user to buy, sell, or hold. "
        "Keep answers concise and useful for a student/demo market dashboard. "
        "If the question asks for a cause that is not present in the supplied context, "
        "say that the current Pulse data does not establish the cause."
    )


def ask_groq(question: str, context: list[dict]) -> str:
    """Call Groq's OpenAI-compatible chat completions endpoint."""
    settings = get_settings()
    if not settings.groq_api_key:
        raise AIServiceError("GROQ_API_KEY is not configured")

    url = settings.groq_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.groq_model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {
                "role": "user",
                "content": (
                    "Answer this Pulse question using only the provided context.\n\n"
                    f"Question: {question}\n\n"
                    f"Pulse context JSON:\n{json.dumps(context, ensure_ascii=False, default=str)}"
                ),
            },
        ],
    }

    try:
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise AIServiceError(f"AI provider request failed: {error}") from error

    try:
        answer = body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as error:
        raise AIServiceError("AI provider returned an unexpected response") from error

    if not answer:
        raise AIServiceError("AI provider returned an empty answer")

    return answer
