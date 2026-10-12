from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.airports import DEFAULT_CSV, read_airports, upsert_airports
from app.models import Airport

CSV_TEXT = """icao,name,type,lat,lon,elevation_m
KMIA,Miami International Airport,large_airport,25.79325,-80.29056,2.4
KXXX,No Elevation Field,small_airport,27.0,-81.0,
"""


def test_read_airports_handles_missing_elevation(tmp_path: Path) -> None:
    path = tmp_path / "airports.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")

    rows = read_airports(path)

    assert rows[0] == {
        "icao": "KMIA",
        "name": "Miami International Airport",
        "type": "large_airport",
        "lat": 25.79325,
        "lon": -80.29056,
        "elevation_m": 2.4,
    }
    assert rows[1]["elevation_m"] is None


def test_upsert_is_idempotent_and_updates(session: Session) -> None:
    row = {
        "icao": "KMIA",
        "name": "Old Name",
        "type": "large_airport",
        "lat": 25.0,
        "lon": -80.0,
        "elevation_m": None,
    }
    upsert_airports(session, [row])
    upsert_airports(session, [row | {"name": "Miami International Airport"}])

    assert session.scalar(select(func.count()).select_from(Airport)) == 1
    assert session.get(Airport, "KMIA").name == "Miami International Airport"


def test_bundled_extract_is_loadable() -> None:
    rows = read_airports(DEFAULT_CSV)

    assert len(rows) > 5000
    assert len({r["icao"] for r in rows}) == len(rows)
    assert any(r["icao"] == "KMIA" for r in rows)
    assert all(-90 <= r["lat"] <= 90 and -180 <= r["lon"] <= 180 for r in rows)
