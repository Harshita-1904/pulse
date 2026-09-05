"""Request and response schemas for the Pulse AI assistant."""

from pydantic import BaseModel, Field


class AIAskRequest(BaseModel):
    """A user's natural-language question for the Pulse assistant."""

    question: str = Field(min_length=1, max_length=1000)


class AIAskResponse(BaseModel):
    """AI answer plus the deterministic Pulse context used to generate it."""

    answer: str
    intent: str
    symbols: list[str]
    data_used: list[dict]
