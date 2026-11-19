"""The dbt project, run end to end on DuckDB over a small synthetic silver table.

Trino stays the production engine. These tests check what CI can check without Docker:
the models compile and build, the dbt tests and unit tests pass, and reloading a month is
idempotent.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from tests.fixtures.load_silver import load_silver

ROOT = Path(__file__).resolve().parent.parent
DBT_DIR = ROOT / "dbt"
DBT = Path(sys.executable).parent / "dbt"


class Warehouse:
    """A DuckDB file standing in for the lakehouse, plus the dbt project pointed at it."""

    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.path = workdir / "lake.duckdb"

    def load_silver(self, where: str = "true") -> None:
        load_silver(self.path, where)

    def sql(self, query: str):
        with duckdb.connect(str(self.path)) as con:
            return con.execute(query).fetchall()

    def dbt(self, *args: str, month: str | None = None) -> subprocess.CompletedProcess:
        command = [
            str(DBT), *args,
            "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR), "--target", "ci",
            "--target-path", str(self.workdir / "target"), "--log-path", str(self.workdir / "logs"),
        ]
        if month:
            command += ["--vars", json.dumps({"month": month})]
        env = {
            **os.environ,
            "DBT_DUCKDB_PATH": str(self.path),
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
        }
        return subprocess.run(command, env=env, capture_output=True, text=True, check=False)

    def build(self) -> None:
        # Unit tests on an incremental model read the columns of the built table, so they run
        # after the build, as in production where they are left out.
        assert_ok(self.dbt("build", "--exclude-resource-type", "unit_test"))

    def months(self) -> dict[str, int]:
        rows = self.sql("select source_month, count(*) from gold.fct_trip group by 1 order by 1")
        return dict(rows)


def assert_ok(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, result.stdout[-3000:]


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Warehouse:
    warehouse = Warehouse(tmp_path_factory.mktemp("dbt_built"))
    warehouse.load_silver()
    warehouse.build()
    assert_ok(warehouse.dbt("test", "--resource-type", "unit_test"))
    return warehouse


@pytest.fixture
def warehouse(tmp_path) -> Warehouse:
    return Warehouse(tmp_path)


def test_unit_tests_ran_and_passed(built):
    # run_results.json describes the last command, the unit tests.
    results = json.loads((built.workdir / "target" / "run_results.json").read_text("utf-8"))
    names = {r["unique_id"].split(".")[-1]: r["status"] for r in results["results"]}
    assert names == {
        "fct_trip_reloads_only_the_requested_month": "pass",
        "fct_trip_loads_new_months_without_a_variable": "pass",
        "dim_date_fills_gaps_and_flags_weekends": "pass",
        "dim_vendor_names_known_operators": "pass",
    }


def test_gold_holds_every_silver_trip_once(built):
    assert built.sql("select count(*) from gold.fct_trip") == built.sql(
        "select count(*) from silver.trips"
    )
    assert built.sql("select count(*) - count(distinct trip_id) from gold.fct_trip") == [(0,)]


def test_reloading_a_month_replaces_it_and_leaves_the_others(warehouse):
    warehouse.load_silver()
    warehouse.build()
    before = warehouse.months()

    # The TLC republishes February: one fare corrected, one trip added.
    warehouse.sql(
        "update silver.trips set total_amount = total_amount + 10 "
        "where source_month = '2024-02' and service = 'green'"
    )
    warehouse.sql(
        "insert into silver.trips select * replace (md5(trip_id) as trip_id) "
        "from silver.trips where source_month = '2024-02' limit 1"
    )
    for _ in range(2):  # the second run stands for an Airflow retry
        assert_ok(warehouse.dbt("run", "--select", "fct_trip", month="2024-02"))
        after = warehouse.months()
        assert after["2024-01"] == before["2024-01"]
        assert after["2024-02"] == before["2024-02"] + 1

    assert warehouse.sql(
        "select count(*) from gold.fct_trip f join silver.trips s using (trip_id) "
        "where f.total_amount <> s.total_amount"
    ) == [(0,)]


def test_a_run_without_month_loads_only_new_months(warehouse):
    warehouse.load_silver(where="source_month = '2024-01'")
    warehouse.build()
    january = warehouse.months()
    assert list(january) == ["2024-01"]

    warehouse.load_silver()
    for _ in range(2):
        assert_ok(warehouse.dbt("run", "--select", "fct_trip"))
        assert warehouse.months()["2024-01"] == january["2024-01"]
        assert set(warehouse.months()) == {"2024-01", "2024-02"}


def test_a_malformed_month_is_refused(built):
    result = built.dbt("run", "--select", "fct_trip", month="2024-13")
    assert result.returncode != 0
    assert "AAAA-MM" in result.stdout
