"""Check silver against its YAML contract. Fails the pipeline when a rule is broken."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import trino
import yaml

CONTRACT = Path(__file__).resolve().parent.parent / "governance" / "contracts" / "silver_trips.yaml"
TABLE = "iceberg.silver.trips"


def contract_checks(contract: dict[str, Any], month: str | None = None) -> list[tuple[str, str]]:
    """Turn a contract into (rule name, SQL returning the number of violations)."""
    scope = f"where source_month = '{month}'" if month else "where true"
    checks = []
    for column in contract["columns"]:
        name = column["name"]
        if not column.get("nullable", True):
            checks.append(
                (f"{name}: non nul", f"select count(*) from {TABLE} {scope} and {name} is null")
            )
        if "min" in column:
            checks.append(
                (
                    f"{name}: >= {column['min']}",
                    f"select count(*) from {TABLE} {scope} and {name} < {column['min']}",
                )
            )
        if "max" in column:
            checks.append(
                (
                    f"{name}: <= {column['max']}",
                    f"select count(*) from {TABLE} {scope} and {name} > {column['max']}",
                )
            )
        if "accepted_values" in column:
            values = ", ".join(f"'{value}'" for value in column["accepted_values"])
            checks.append(
                (
                    f"{name}: valeurs admises",
                    f"select count(*) from {TABLE} {scope} and {name} not in ({values})",
                )
            )
    keys = ", ".join(contract["primary_key"])
    # Grouping on a 64-bit hash keeps 70 million keys in memory, for a negligible collision risk.
    hashed = f"xxhash64(to_utf8(concat_ws('|', {keys})))"
    checks.append(
        (
            f"clé primaire : {keys}",
            f"select count(*) from (select {hashed} as key_hash from {TABLE} {scope} "
            f"group by 1 having count(*) > 1)",
        )
    )
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", default=None)
    args = parser.parse_args()
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    connection = trino.dbapi.connect(
        host=os.environ.get("TRINO_HOST", "localhost"), port=8080, user="engineer"
    )
    cursor = connection.cursor()
    cursor.execute(f"select distinct source_month from {TABLE} order by 1")
    # Months are disjoint, so per-month checks also hold for the whole table and fit in memory.
    months = [args.month] if args.month else [row[0] for row in cursor.fetchall()]
    failures = 0
    for month in months:
        for name, sql in contract_checks(contract, month):
            cursor.execute(sql)
            violations = cursor.fetchone()[0]
            print(f"{'OK ' if violations == 0 else 'KO '} {month} {name} ({violations})")
            failures += violations > 0
    print(f"{failures} règle(s) en échec sur {len(months)} mois")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
