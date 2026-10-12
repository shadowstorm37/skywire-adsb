"""Load data/airports.csv into the airports table. Safe to run repeatedly."""

import argparse
from pathlib import Path

from app.airports import DEFAULT_CSV, read_airports, upsert_airports
from app.db import get_sessionmaker


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    rows = read_airports(args.csv)
    with get_sessionmaker().begin() as session:
        count = upsert_airports(session, rows)
    print(f"Loaded {count} airports from {args.csv}")


if __name__ == "__main__":
    main()
