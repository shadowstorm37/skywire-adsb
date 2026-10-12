"""ORM models. Schema changes go through Alembic; tests check the two stay in sync."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ANOMALY_STATUSES = ("open", "reviewed", "dismissed")
ANOMALY_SEVERITIES = ("low", "medium", "high")

# Explicit names so migrations can refer to constraints deterministically.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Aircraft(Base):
    __tablename__ = "aircraft"

    icao24: Mapped[str] = mapped_column(String(6), primary_key=True)
    callsign: Mapped[str | None] = mapped_column(String(8))
    origin_country: Mapped[str | None] = mapped_column(String(64))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (
        # Deduplication key. Its backing index also serves (icao24, position_time)
        # lookups, so no second index is declared on the same columns.
        UniqueConstraint("icao24", "position_time"),
        Index("ix_positions_position_time", "position_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    icao24: Mapped[str] = mapped_column(ForeignKey("aircraft.icao24"))
    # When the position itself was last updated, which can be older than last_contact.
    position_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_contact: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lat: Mapped[float | None]
    lon: Mapped[float | None]
    baro_altitude: Mapped[float | None]
    geo_altitude: Mapped[float | None]
    velocity: Mapped[float | None]
    heading: Mapped[float | None]
    vertical_rate: Mapped[float | None]
    on_ground: Mapped[bool | None]
    squawk: Mapped[str | None] = mapped_column(String(4))


class Anomaly(Base):
    __tablename__ = "anomalies"
    __table_args__ = (
        CheckConstraint(_in_list("status", ANOMALY_STATUSES), name="status"),
        CheckConstraint(_in_list("severity", ANOMALY_SEVERITIES), name="severity"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="confidence_range"),
        Index("ix_anomalies_detected_at", "detected_at"),
        Index("ix_anomalies_icao24", "icao24"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    icao24: Mapped[str] = mapped_column(ForeignKey("aircraft.icao24"))
    type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float]
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"))
    status: Mapped[str] = mapped_column(String(16), server_default="open")


class Airport(Base):
    """Reference data from OurAirports, used to suppress false positives near airports."""

    __tablename__ = "airports"

    icao: Mapped[str] = mapped_column(String(4), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(16))
    lat: Mapped[float]
    lon: Mapped[float]
    elevation_m: Mapped[float | None]
