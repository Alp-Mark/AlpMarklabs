from __future__ import annotations

import os
from logging.config import fileConfig

from backend.app.db import models  # noqa: F401
from backend.app.db.base import Base
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_database_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://alpmark:alpmark@localhost:5432/alpmark",
    )
    # Hosts like Railway provide "postgresql://" / "postgres://" URLs, which
    # SQLAlchemy maps to psycopg2. This app uses psycopg (v3), so force the
    # "+psycopg" driver suffix.
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


config.set_main_option("sqlalchemy.url", get_database_url())
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _run_migrations(connection)


def _run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
