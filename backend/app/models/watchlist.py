"""Watchlist ownership, membership, and user-specific stock state models."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Watchlist(Base):
    """A named collection of stocks owned by a user."""

    __tablename__ = "watchlists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="My Watchlist", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="watchlists")
    entries: Mapped[list["WatchlistStock"]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan"
    )


class WatchlistStock(Base):
    """Many-to-many membership between watchlists and stocks."""

    __tablename__ = "watchlist_stocks"
    __table_args__ = (UniqueConstraint("watchlist_id", "stock_id", name="uq_watchlist_stock"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    watchlist_id: Mapped[str] = mapped_column(ForeignKey("watchlists.id"), nullable=False)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    watchlist: Mapped[Watchlist] = relationship(back_populates="entries")
    stock: Mapped["Stock"] = relationship(back_populates="watchlist_entries")


class UserStockState(Base):
    """Per-user checkpoint used to calculate changes since last seen."""

    __tablename__ = "user_stock_state"
    __table_args__ = (UniqueConstraint("user_id", "stock_id", name="uq_user_stock_state"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_price: Mapped[float | None] = mapped_column(Float)
    last_seen_volume: Mapped[float | None] = mapped_column(Float)

    user: Mapped["User"] = relationship(back_populates="stock_states")
    stock: Mapped["Stock"] = relationship()
