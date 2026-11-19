"""The DAG loads in a real Airflow, and Cosmos renders one task per dbt node.

Runs in its own CI job, with Airflow and Cosmos installed apart from the project's venv:
    LAKEHOUSE_ROOT=. LAKE_TOOLS=.venv/bin pytest airflow/tests
"""

import os
from pathlib import Path

import pytest

# Cosmos caches the dbt ls output in Airflow Variables, which needs a metadata database.
os.environ.setdefault("AIRFLOW__COSMOS__ENABLE_CACHE_DBT_LS", "False")
os.environ.setdefault("AIRFLOW__CORE__LOAD_EXAMPLES", "False")

# The FAB import registers the user table that dag_run_note references, for dag.test().
import airflow.providers.fab.auth_manager.models  # noqa: E402, F401
from airflow.models import DagBag  # noqa: E402

DAGS = Path(__file__).resolve().parent.parent / "dags"


@pytest.fixture(scope="module")
def dag():
    bag = DagBag(dag_folder=str(DAGS), include_examples=False)
    assert bag.import_errors == {}
    # bag.dags, not bag.get_dag(): the latter queries the metadata database.
    return bag.dags["monthly_lakehouse"]


def test_one_task_per_dbt_model_with_its_tests(dag):
    ids = set(dag.task_ids)
    for model in ["fct_trip", "dim_date", "dim_zone", "dim_vendor", "dim_payment"]:
        assert {f"dbt_gold.{model}.run", f"dbt_gold.{model}.test"} <= ids
    # A model without tests is a single task.
    assert {"dbt_gold.stg_trips_run", "dbt_gold.taxi_zone_lookup_seed"} <= ids


def test_relationship_tests_run_after_both_models(dag):
    task = dag.get_task(
        "dbt_gold.relationships_fct_trip_pickup_zone_id__zone_id__ref_dim_zone__test"
    )
    assert task.upstream_task_ids == {"dbt_gold.fct_trip.test", "dbt_gold.dim_zone.test"}


def test_gold_waits_for_silver_to_be_checked_and_compacted(dag):
    chain = ["ingest_bronze", "bronze_to_silver", "check_contract", "compact_silver"]
    for upstream, downstream in zip(chain, chain[1:], strict=False):
        assert upstream in dag.get_task(downstream).upstream_task_ids
    dbt_roots = [t for t in dag.tasks if t.task_id.startswith("dbt_gold.") and
                 not any(u.startswith("dbt_gold.") for u in t.upstream_task_ids)]
    assert dbt_roots
    assert all(t.upstream_task_ids == {"compact_silver"} for t in dbt_roots)


def test_fct_trip_reloads_the_month_of_the_run(dag):
    run = dag.get_task("dbt_gold.fct_trip.run")
    assert "ds_add(ds, -60)" in run.vars["month"]
    assert "vars" in run.template_fields


def test_unit_tests_stay_out_of_production_runs(dag):
    assert dag.get_task("dbt_gold.fct_trip.test").env["DBT_EXCLUDE_RESOURCE_TYPES"] == "unit_test"


def test_cosmos_runs_the_dbt_tasks_and_reloads_the_run_month(tmp_path, monkeypatch):
    """The dbt task group, executed by Airflow on the DuckDB target over the fixture."""
    import json
    import subprocess

    import pendulum

    root = Path(os.environ["LAKEHOUSE_ROOT"])
    tools = Path(os.environ["LAKE_TOOLS"])
    lake = tmp_path / "lake.duckdb"
    loader = [str(tools / "python"), str(root / "tests/fixtures/load_silver.py"), str(lake)]
    subprocess.run(loader, check=True)
    monkeypatch.setenv("LAKE_DBT_TARGET", "ci")
    monkeypatch.setenv("DBT_DUCKDB_PATH", str(lake))
    dag = DagBag(dag_folder=str(DAGS), include_examples=False).dags["monthly_lakehouse"]

    # First run, on an empty lake: every model and test of the group.
    gold = dag.partial_subset(r"^dbt_gold\.", include_upstream=False)
    assert gold.test(execution_date=pendulum.datetime(2024, 4, 5, tz="UTC")).state == "success"

    # February is corrected upstream. A run on 2024-04-05 targets 2024-02 (minus 60 days).
    subprocess.run([*loader, "--where", "not (source_month = '2024-02' and service = 'green')"],
                   check=True)
    fct = dag.partial_subset(r"^dbt_gold\.fct_trip\.", include_upstream=False)
    assert fct.test(execution_date=pendulum.datetime(2024, 4, 5, 12, tz="UTC")).state == "success"

    # Read with the project's DuckDB, the version that wrote the file.
    count = (
        "import duckdb, json, sys; con = duckdb.connect(sys.argv[1], read_only=True); "
        "q = 'select source_month, count(*) from {} group by 1 order by 1'; "
        "print(json.dumps([dict(con.execute(q.format(t)).fetchall()) "
        "for t in ('gold.fct_trip', 'silver.trips')]))"
    )
    out = subprocess.run([str(tools / "python"), "-c", count, str(lake)],
                         check=True, capture_output=True, text=True).stdout
    gold_months, silver_months = json.loads(out)
    assert gold_months == silver_months
    assert gold_months["2024-02"] == 6  # one green February trip fewer than the fixture
