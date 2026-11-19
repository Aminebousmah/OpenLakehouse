"""Monthly run: bronze, silver, quality, compaction, gold. A retry never duplicates a row.

The gold layer is rendered by Cosmos: one Airflow task per dbt model, followed by its tests,
so a failure points at a model and a retry reruns only that model.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow.operators.bash import BashOperator
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import ExecutionMode, InvocationMode, LoadMode, TestBehavior

from airflow import DAG

# TLC publishes each month with about two months of delay.
MONTH = "{{ macros.ds_format(macros.ds_add(ds, -60), '%Y-%m-%d', '%Y-%m') }}"
ROOT = Path(os.environ.get("LAKEHOUSE_ROOT", "/opt/lakehouse"))
# The pipeline tools, dbt included, live in their own venv, apart from Airflow's dependencies.
TOOLS = Path(os.environ.get("LAKE_TOOLS", "/opt/airflow/lake-venv/bin"))
SPARK = "docker exec openlakehouse-spark-1 /opt/spark/bin/spark-submit"
DBT = str(TOOLS / "dbt")
# trino in production; the DAG test switches it to the DuckDB target to run Cosmos for real.
DBT_TARGET = os.environ.get("LAKE_DBT_TARGET", "trino")

with DAG(
    dag_id="monthly_lakehouse",
    description="Chargement mensuel des trajets TLC, de bronze à gold",
    start_date=datetime(2024, 1, 1),
    schedule="0 6 5 * *",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["lakehouse"],
) as dag:
    ingest = BashOperator(
        task_id="ingest_bronze",
        bash_command=f"cd {ROOT} && {TOOLS}/python ingestion/download.py --months {MONTH}",
    )
    silver = BashOperator(
        task_id="bronze_to_silver",
        bash_command=f"{SPARK} /opt/spark_jobs/bronze_to_silver.py --month {MONTH}",
    )
    quality = BashOperator(
        task_id="check_contract",
        bash_command=f"cd {ROOT} && {TOOLS}/python quality/check_contract.py --month {MONTH}",
    )
    compaction = BashOperator(
        task_id="compact_silver",
        bash_command=f"{SPARK} /opt/spark_jobs/maintenance.py",
    )
    gold = DbtTaskGroup(
        group_id="dbt_gold",
        project_config=ProjectConfig(
            ROOT / "dbt",
            # No dbt packages to install, so no dbt deps at parse time or at run time.
            install_dbt_deps=False,
            # Unit tests run in CI, on DuckDB, not against production data.
            env_vars={"DBT_EXCLUDE_RESOURCE_TYPES": "unit_test"},
        ),
        profile_config=ProfileConfig(
            profile_name="openlakehouse",
            target_name=DBT_TARGET,
            profiles_yml_filepath=ROOT / "dbt" / "profiles.yml",
        ),
        execution_config=ExecutionConfig(
            execution_mode=ExecutionMode.LOCAL,
            invocation_mode=InvocationMode.SUBPROCESS,
            dbt_executable_path=DBT,
        ),
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            invocation_mode=InvocationMode.SUBPROCESS,
            dbt_executable_path=DBT,
            test_behavior=TestBehavior.AFTER_EACH,
            # fct_trip's relationship tests also need dim_zone and dim_payment: they get their
            # own tasks, after every model they read.
            should_detach_multiple_parents_tests=True,
            emit_datasets=False,
        ),
        operator_args={
            # fct_trip reloads exactly the month the upstream tasks just wrote.
            "vars": {"month": MONTH},
        },
    )

    ingest >> silver >> quality >> compaction >> gold
