"""Small, explicit schema upgrades for the hackathon development database.

Replace this module with versioned Alembic migrations before production use.
"""

from sqlalchemy import text

from app.database.session import engine


def main() -> None:
    """Apply backwards-compatible schema additions required by the dashboard."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE user_stock_state "
                "ADD COLUMN IF NOT EXISTS last_seen_price DOUBLE PRECISION"
            )
        )
        connection.execute(
            text("ALTER TABLE price_history ADD COLUMN IF NOT EXISTS volume DOUBLE PRECISION")
        )
        connection.execute(
            text(
                "ALTER TABLE market_data ADD COLUMN IF NOT EXISTS status VARCHAR(16) "
                "NOT NULL DEFAULT 'fresh'"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE user_stock_state "
                "ADD COLUMN IF NOT EXISTS last_seen_volume DOUBLE PRECISION"
            )
        )


if __name__ == "__main__":
    main()
