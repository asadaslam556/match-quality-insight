"""Database access.

The API is read-only and every endpoint is an aggregation over the scored_applications
view, so there are no ORM models here. SQLAlchemy is used for connection pooling and
parameter binding; the queries themselves live as plain .sql files under metrics/sql.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionFactory() as session:
        yield session
