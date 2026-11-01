#!/bin/sh
# One month through bronze, silver, quality and gold, without Airflow: ./scripts/run_month.sh 2024-01
set -e
MONTH="$1"
COMPOSE="docker compose -f infra/docker-compose.yml"

uv run python ingestion/download.py --months "$MONTH"
$COMPOSE exec -T spark /opt/spark/bin/spark-submit /opt/spark_jobs/bronze_to_silver.py --month "$MONTH"
uv run python quality/check_contract.py --month "$MONTH"
$COMPOSE exec -T spark /opt/spark/bin/spark-submit /opt/spark_jobs/maintenance.py
(cd dbt && uv run dbt build --profiles-dir .)
