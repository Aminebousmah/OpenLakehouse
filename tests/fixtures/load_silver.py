"""Load the synthetic silver fixture into a DuckDB file, to run dbt without Docker.

    uv run python tests/fixtures/load_silver.py dbt/target/ci.duckdb

Then run dbt with --target ci and DBT_DUCKDB_PATH=target/ci.duckdb, as the README shows.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "silver_trips.csv"
CONTRACT = ROOT / "governance" / "contracts" / "silver_trips.yaml"


def load_silver(database: Path, where: str = "true") -> None:
    """(Re)create silver.trips from the fixture, typed as the data contract says."""
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    columns = {c["name"]: c["type"] for c in contract["columns"]}
    database.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database)) as con:
        con.execute("create schema if not exists silver")
        con.execute(
            "create or replace table silver.trips as "
            f"select * from read_csv(?, header = true, columns = {columns!r}) where {where}",
            [str(FIXTURE)],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--where", default="true", help="filtre SQL sur les lignes chargées")
    args = parser.parse_args()
    load_silver(args.database, args.where)
