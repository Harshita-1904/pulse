"""Create local development tables without a migration framework."""

from app.database.base import Base
from app.database.session import engine
import app.models  # noqa: F401 - registers models with the declarative metadata.


def main() -> None:
    """Create every currently registered model table."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
