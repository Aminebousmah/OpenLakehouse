#!/bin/sh
set -e
superset db upgrade
superset fab create-admin --username admin --firstname Admin --lastname Local \
  --email admin@example.test --password "${SUPERSET_ADMIN_PASSWORD:-admin}" || true
superset init
superset set_database_uri -d lakehouse -u "trino://analyst@trino:8080/iceberg/gold" || true
exec gunicorn -b 0.0.0.0:8088 -w 2 --timeout 120 "superset.app:create_app()"
