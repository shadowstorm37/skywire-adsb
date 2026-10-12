"""Loading the airports reference table from the bundled OurAirports extract."""

import csv
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Airport

DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data" / "airports.csv"


def read_airports(path: Path = DEFAULT_CSV) -> list[dict]:
    """Parse the extract into rows ready for insertion. Elevation may be missing."""
    with path.open(newline="", encoding="utf-8") as f:
        return [
            {
                "icao": row["icao"],
                "name": row["name"],
                "type": row["type"],
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "elevation_m": float(row["elevation_m"]) if row["elevation_m"] else None,
            }
            for row in csv.DictReader(f)
        ]


def upsert_airports(session: Session, rows: list[dict]) -> int:
    """Insert or update airports by ICAO code, so reloading is safe. Returns rows written."""
    if not rows:
        return 0
    stmt = insert(Airport)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Airport.icao],
        set_={c: stmt.excluded[c] for c in ("name", "type", "lat", "lon", "elevation_m")},
    )
    session.execute(stmt, rows)
    return len(rows)
