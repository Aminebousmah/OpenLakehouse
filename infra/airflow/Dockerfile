FROM apache/airflow:2.10.5-python3.12

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*
USER airflow
# Cosmos goes into Airflow's own environment, pinned by Airflow's constraints.
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" "astronomer-cosmos~=1.15.0" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-3.12.txt"
# The pipeline tools, dbt included, live apart from Airflow, so their dependencies never collide.
RUN python -m venv /opt/airflow/lake-venv \
    && /opt/airflow/lake-venv/bin/pip install --no-cache-dir \
       "boto3>=1.34" "httpx>=0.27" "trino>=0.329" "pyyaml>=6" "dbt-trino>=1.8"
