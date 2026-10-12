from datetime import UTC, datetime

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Aircraft, Anomaly, Base, Position

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def make_aircraft(session: Session, icao24: str = "a1b2c3") -> Aircraft:
    aircraft = Aircraft(icao24=icao24, callsign="TEST123", first_seen=T0, last_seen=T0)
    session.add(aircraft)
    session.flush()
    return aircraft


def test_migrations_match_models(engine: Engine) -> None:
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_duplicate_position_is_rejected(session: Session) -> None:
    make_aircraft(session)
    session.add(Position(icao24="a1b2c3", position_time=T0, last_contact=T0))
    session.flush()

    session.add(Position(icao24="a1b2c3", position_time=T0, last_contact=T0))
    with pytest.raises(IntegrityError):
        session.flush()


def test_same_time_for_different_aircraft_is_allowed(session: Session) -> None:
    make_aircraft(session, "a1b2c3")
    make_aircraft(session, "d4e5f6")
    session.add(Position(icao24="a1b2c3", position_time=T0, last_contact=T0))
    session.add(Position(icao24="d4e5f6", position_time=T0, last_contact=T0))
    session.flush()


def test_position_requires_known_aircraft(session: Session) -> None:
    session.add(Position(icao24="ffffff", position_time=T0, last_contact=T0))
    with pytest.raises(IntegrityError):
        session.flush()


def test_anomaly_defaults(session: Session) -> None:
    make_aircraft(session)
    anomaly = Anomaly(icao24="a1b2c3", type="emergency_squawk", severity="high", confidence=1.0)
    session.add(anomaly)
    session.flush()
    session.refresh(anomaly)

    assert anomaly.status == "open"
    assert anomaly.details == {}
    assert anomaly.detected_at is not None
    assert anomaly.position_id is None


@pytest.mark.parametrize(
    "overrides",
    [{"status": "closed"}, {"severity": "critical"}, {"confidence": 1.5}],
)
def test_anomaly_rejects_invalid_values(session: Session, overrides: dict) -> None:
    make_aircraft(session)
    values = {"icao24": "a1b2c3", "type": "x", "severity": "low", "confidence": 0.5} | overrides
    session.add(Anomaly(**values))
    with pytest.raises(IntegrityError):
        session.flush()
