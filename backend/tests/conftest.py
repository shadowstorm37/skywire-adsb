"""Database fixtures.

Tests run against real PostgreSQL because the behaviour under test (unique
constraints, JSONB, ON CONFLICT) is Postgres-specific. They use a separate
`<database>_test` database on the configured server, rebuilt from the Alembic
migrations each session, so the development data is never touched.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

from app.settings import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    base_url = make_url(get_settings().database_url)
    test_url = base_url.set(database=f"{base_url.database}_test")

    admin = create_engine(base_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{test_url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    admin.dispose()

    config = Config(BACKEND_DIR / "alembic.ini")
    # configparser treats % as interpolation, so escape any in the password.
    config.set_main_option(
        "sqlalchemy.url", test_url.render_as_string(hide_password=False).replace("%", "%%")
    )
    command.upgrade(config, "head")

    engine = create_engine(test_url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose work is rolled back after the test, including its commits."""
    with engine.connect() as conn:
        transaction = conn.begin()
        with Session(conn, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
