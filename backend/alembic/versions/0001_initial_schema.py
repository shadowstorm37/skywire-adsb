"""Initial schema: aircraft, positions, anomalies, airports.

Revision ID: 0001
Revises:
Create Date: 2026-10-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "aircraft",
        sa.Column("icao24", sa.String(6), nullable=False),
        sa.Column("callsign", sa.String(8), nullable=True),
        sa.Column("origin_country", sa.String(64), nullable=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("icao24", name="pk_aircraft"),
    )

    op.create_table(
        "airports",
        sa.Column("icao", sa.String(4), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("elevation_m", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("icao", name="pk_airports"),
    )

    op.create_table(
        "positions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("icao24", sa.String(6), nullable=False),
        sa.Column("position_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_contact", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("baro_altitude", sa.Float(), nullable=True),
        sa.Column("geo_altitude", sa.Float(), nullable=True),
        sa.Column("velocity", sa.Float(), nullable=True),
        sa.Column("heading", sa.Float(), nullable=True),
        sa.Column("vertical_rate", sa.Float(), nullable=True),
        sa.Column("on_ground", sa.Boolean(), nullable=True),
        sa.Column("squawk", sa.String(4), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_positions"),
        sa.ForeignKeyConstraint(
            ["icao24"], ["aircraft.icao24"], name="fk_positions_icao24_aircraft"
        ),
        # Deduplication key; its index also covers (icao24, position_time) lookups.
        sa.UniqueConstraint("icao24", "position_time", name="uq_positions_icao24_position_time"),
    )
    op.create_index("ix_positions_position_time", "positions", ["position_time"])

    op.create_table(
        "anomalies",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("icao24", sa.String(6), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "details",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("position_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(16), server_default="open", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_anomalies"),
        sa.ForeignKeyConstraint(
            ["icao24"], ["aircraft.icao24"], name="fk_anomalies_icao24_aircraft"
        ),
        sa.ForeignKeyConstraint(
            ["position_id"], ["positions.id"], name="fk_anomalies_position_id_positions"
        ),
        sa.CheckConstraint(
            "status IN ('open', 'reviewed', 'dismissed')", name="ck_anomalies_status"
        ),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high')", name="ck_anomalies_severity"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_anomalies_confidence_range"),
    )
    op.create_index("ix_anomalies_detected_at", "anomalies", ["detected_at"])
    op.create_index("ix_anomalies_icao24", "anomalies", ["icao24"])


def downgrade() -> None:
    op.drop_table("anomalies")
    op.drop_table("positions")
    op.drop_table("airports")
    op.drop_table("aircraft")
