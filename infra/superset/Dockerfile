FROM apache/superset:4.1.4

USER root
RUN pip install --no-cache-dir "trino[sqlalchemy]==0.329.0"
COPY bootstrap.sh /app/bootstrap.sh
RUN chmod +x /app/bootstrap.sh
USER superset
ENTRYPOINT ["/app/bootstrap.sh"]
