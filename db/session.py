from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import get_settings


settings = get_settings()

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables.

    For the MVP we use SQLAlchemy's metadata create_all on startup.
    """

    from db.models import Base  # noqa: WPS433 - imported for side effects

    Base.metadata.create_all(bind=engine)
