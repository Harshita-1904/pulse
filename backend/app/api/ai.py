"""Authenticated AI assistant endpoint for Pulse."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DatabaseSession
from app.schemas.ai import AIAskRequest, AIAskResponse
from app.services.ai_service import AIServiceError, ask_groq, collect_context


router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ask", response_model=AIAskResponse)
def ask_ai(
    payload: AIAskRequest,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> AIAskResponse:
    """Answer a Pulse question using deterministic watchlist intelligence as context."""
    try:
        intent, symbols, context = collect_context(database, current_user.id, payload.question)
        answer = ask_groq(payload.question, context)
    except AIServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    return AIAskResponse(
        answer=answer,
        intent=intent,
        symbols=symbols,
        data_used=context,
    )
