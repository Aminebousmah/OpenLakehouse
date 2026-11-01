"""Reproducible benchmarks: same queries on partitioned or not, compacted or not.

Variants are built from silver with Trino, and raw timings are kept next to the report.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

import trino

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from benchmarks.queries import QUERIES  # noqa: E402
from benchmarks.stats import median, percentile  # noqa: E402

SOURCE = "iceberg.silver.trips"
SCHEMA = "iceberg.benchmark"
COLUMNS = (
    "trip_id, service, vendor_id, pickup_ts, dropoff_ts, pickup_zone_id, dropoff_zone_id, "
    "passenger_count, trip_distance_miles, payment_type, fare_amount, tip_amount, total_amount, "
    "duration_minutes, source_month"
)
VARIANTS = {
    "non_partitioned": "array[]",
    "partitioned_days": "array['day(pickup_ts)']",
    "partitioned_months": "array['month(pickup_ts)']",
}
SMALL_FILE_BATCHES = 40
# Fragmentation is tested on one month, the one every filtered query reads.
FRAGMENT_MONTH = "2024-02"


def connect():
    # Fewer parallel writers keep partitioned writes in memory. Reads are not affected.
    connection = trino.dbapi.connect(
        host=os.environ.get("TRINO_HOST", "localhost"), port=8080, user="engineer",
        catalog="iceberg", schema="benchmark",
        session_properties={"task_max_writer_count": "4"},
    )
    return connection.cursor()


def execute(cursor, sql: str) -> list:
    cursor.execute(sql)
    return cursor.fetchall()


def build_variants(cursor) -> None:
    execute(cursor, f"create schema if not exists {SCHEMA}")
    months = [row[0] for row in execute(cursor, f"select distinct source_month from {SOURCE}")]
    for name, partitioning in VARIANTS.items():
        execute(cursor, f"drop table if exists {SCHEMA}.{name}")
        execute(
            cursor,
            f"create table {SCHEMA}.{name} with (partitioning = {partitioning}) "
            f"as select {COLUMNS} from {SOURCE} where false",
        )
        # Month by month, like the real pipeline.
        for month in sorted(months):
            execute(
                cursor,
                f"insert into {SCHEMA}.{name} select {COLUMNS} from {SOURCE} "
                f"where source_month = '{month}'",
            )
    build_fragmented(cursor)
    # Same data as the fragmented table, once compacted.
    execute(cursor, f"drop table if exists {SCHEMA}.compacted")
    execute(
        cursor,
        f"create table {SCHEMA}.compacted with (partitioning = array['day(pickup_ts)']) "
        f"as select * from {SCHEMA}.fragmented",
    )
    execute(cursor, f"alter table {SCHEMA}.compacted execute optimize")


def build_fragmented(cursor) -> None:
    """Many small inserts: what a pipeline without maintenance leaves behind."""
    execute(cursor, f"drop table if exists {SCHEMA}.fragmented")
    execute(
        cursor,
        f"create table {SCHEMA}.fragmented with (partitioning = array['day(pickup_ts)']) "
        f"as select {COLUMNS} from {SOURCE} where false",
    )
    for batch in range(SMALL_FILE_BATCHES):
        execute(
            cursor,
            f"insert into {SCHEMA}.fragmented select {COLUMNS} from {SOURCE} "
            f"where source_month = '{FRAGMENT_MONTH}' "
            f"and abs(mod(from_big_endian_64(substr(from_hex(trip_id), 1, 8)), "
            f"{SMALL_FILE_BATCHES})) = {batch}",
        )


def table_stats(cursor, name: str) -> dict[str, float]:
    rows = execute(cursor, f'select count(*), sum(file_size_in_bytes) from "{name}$files"')
    count = execute(cursor, f"select count(*) from {SCHEMA}.{name}")[0][0]
    return {"rows": count, "files": rows[0][0], "size_bytes": rows[0][1]}


def run_queries(cursor, tables: list[str], runs: int) -> list[dict]:
    records = []
    for table in tables:
        for query_name, template in QUERIES.items():
            sql = template.format(table=f"{SCHEMA}.{table}")
            for attempt in range(runs + 1):
                start = time.perf_counter()
                execute(cursor, sql)
                elapsed = time.perf_counter() - start
                # The first run warms the caches and is not counted.
                if attempt > 0:
                    records.append({"table": table, "query": query_name, "seconds": elapsed})
    return records


def summarise(records: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[float]] = {}
    for record in records:
        groups.setdefault((record["table"], record["query"]), []).append(record["seconds"])
    return [
        {
            "table": table,
            "query": query,
            "runs": len(values),
            "median_s": round(median(values), 3),
            "p95_s": round(percentile(values, 0.95), 3),
        }
        for (table, query), values in sorted(groups.items())
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", required=True, help="Libellé de volumétrie, par exemple 3m")
    parser.add_argument("--runs", type=int, default=7)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    cursor = connect()
    if not args.skip_build:
        build_variants(cursor)
    tables = [*VARIANTS, "fragmented", "compacted"]
    records = run_queries(cursor, tables, args.runs)
    report = {
        "scale": args.scale,
        "runs_per_query": args.runs,
        "machine": {
            "platform": platform.platform(),
            "cpus": os.cpu_count(),
            "docker_memory_note": os.environ.get("BENCH_MEMORY_NOTE", ""),
        },
        "tables": {table: table_stats(cursor, table) for table in tables},
        "summary": summarise(records),
        "raw": records,
    }
    out = ROOT / "benchmarks" / "results"
    out.mkdir(exist_ok=True)
    path = out / f"results_{args.scale}.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("tables", "summary")}, indent=2, default=str))


if __name__ == "__main__":
    main()
