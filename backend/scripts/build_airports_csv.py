"""Rebuild data/airports.csv from the OurAirports dataset (public domain).

Keeps large, medium and small airports that have an ICAO code. Heliports, seaplane
bases, closed fields and strips without an ICAO code are dropped, so the table is
not a complete list of places an aircraft can land. See docs/limitations.md.

Only needed to refresh the bundled extract; the app itself never downloads this.
"""

import argparse
import csv
import io
import urllib.request
from pathlib import Path

SOURCE_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "airports.csv"
# Order matters: when two rows share an ICAO code, the earlier type wins.
KEPT_TYPES = ("large_airport", "medium_airport", "small_airport")
FEET_TO_METERS = 0.3048


def fetch_source(source: str) -> str:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=60) as response:
            return response.read().decode("utf-8")
    return Path(source).read_text(encoding="utf-8")


def build_rows(source_csv: str) -> list[dict]:
    by_icao: dict[str, dict] = {}
    for row in csv.DictReader(io.StringIO(source_csv)):
        icao = row["icao_code"].strip().upper()
        if row["type"] not in KEPT_TYPES or len(icao) != 4:
            continue
        current = by_icao.get(icao)
        if current and KEPT_TYPES.index(current["type"]) <= KEPT_TYPES.index(row["type"]):
            continue
        elevation_ft = row["elevation_ft"].strip()
        by_icao[icao] = {
            "icao": icao,
            "name": row["name"].strip()[:128],
            "type": row["type"],
            "lat": round(float(row["latitude_deg"]), 5),
            "lon": round(float(row["longitude_deg"]), 5),
            "elevation_m": round(float(elevation_ft) * FEET_TO_METERS, 1) if elevation_ft else "",
        }
    return [by_icao[icao] for icao in sorted(by_icao)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=SOURCE_URL, help="URL or local path to airports.csv")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    rows = build_rows(fetch_source(args.source))
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} airports to {args.output}")


if __name__ == "__main__":
    main()
