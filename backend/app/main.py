"""FastAPI application entry point for Pulse."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.ai import router as ai_router
from app.api.changes import router as changes_router
from app.api.stocks import router as stocks_router
from app.api.overview import router as overview_router
from app.api.watchlists import router as watchlists_router
from app.core.config import get_cors_origins, get_settings
from app.database.base import Base
from app.database.session import engine
import app.models  # noqa: F401 - imports models for metadata registration.
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://pulse-self-psi.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Optionally create local development tables before serving requests."""
    settings = get_settings()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if settings.auto_migrate:
        from app.database.migrate import main as migrate_schema

        migrate_schema()
    yield


app = FastAPI(
    title="Pulse API",
    version="0.1.0",
    description="Backend API for the Pulse smart market watchlist.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(changes_router)
app.include_router(stocks_router)
app.include_router(watchlists_router)
app.include_router(overview_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Return a minimal liveness response for local and deployed environments."""
    return {"status": "ok"}
