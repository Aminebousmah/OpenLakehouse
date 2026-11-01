FROM apache/airflow:2.10.5-python3.12

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*
USER airflow
# The pipeline tools live apart from Airflow, so their dependencies never collide.
RUN python -m venv /opt/airflow/lake-venv \
    && /opt/airflow/lake-venv/bin/pip install --no-cache-dir \
       "boto3>=1.34" "httpx>=0.27" "trino>=0.329" "pyyaml>=6" "dbt-trino>=1.8"
