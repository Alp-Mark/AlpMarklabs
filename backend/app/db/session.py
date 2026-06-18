import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def _normalize_database_url(url: str) -> str:
    # Hosts like Railway provide URLs starting with "postgresql://" or
    # "postgres://", which SQLAlchemy maps to the psycopg2 driver. This app uses
    # psycopg (v3), so force the "+psycopg" driver suffix.
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


DATABASE_URL = _normalize_database_url(
    os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://alpmark:alpmark@localhost:5432/alpmark",
    )
)

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


