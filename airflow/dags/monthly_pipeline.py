"""Monthly run: bronze, silver, quality, compaction, gold. A retry never duplicates a row."""

from datetime import datetime, timedelta

from airflow.operators.bash import BashOperator

from airflow import DAG

# TLC publishes each month with about two months of delay.
MONTH = "{{ macros.ds_format(macros.ds_add(ds, -60), '%Y-%m-%d', '%Y-%m') }}"
ROOT = "/opt/lakehouse"
TOOLS = "/opt/airflow/lake-venv/bin"
SPARK = "docker exec openlakehouse-spark-1 /opt/spark/bin/spark-submit"

with DAG(
    dag_id="monthly_lakehouse",
    description="Chargement mensuel des trajets TLC, de bronze à gold",
    start_date=datetime(2024, 1, 1),
    schedule="0 6 5 * *",
    catchup=False,
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
    gold = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {ROOT}/dbt && {TOOLS}/dbt deps --profiles-dir . --target-path /tmp/dbt "
            f"--log-path /tmp/dbt-logs --quiet; {TOOLS}/dbt build --profiles-dir . "
            "--target-path /tmp/dbt --log-path /tmp/dbt-logs"
        ),
    )

    ingest >> silver >> quality >> compaction >> gold
