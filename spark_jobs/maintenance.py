"""Iceberg maintenance: compact small files, expire old snapshots, drop orphan files."""

from datetime import datetime, timedelta, timezone

from pyspark.sql import SparkSession

TABLE = "silver.trips"
TARGET_FILE_BYTES = 256 * 1024 * 1024
SNAPSHOT_RETENTION_DAYS = 7


def main() -> None:
    spark = SparkSession.builder.appName("iceberg_maintenance").getOrCreate()
    spark.sql(
        f"""
        call lake.system.rewrite_data_files(
            table => '{TABLE}',
            options => map('target-file-size-bytes', '{TARGET_FILE_BYTES}', 'min-input-files', '2')
        )
        """
    ).show(truncate=False)
    limit = datetime.now(timezone.utc) - timedelta(days=SNAPSHOT_RETENTION_DAYS)
    spark.sql(
        f"""
        call lake.system.expire_snapshots(
            table => '{TABLE}',
            older_than => timestamp '{limit:%Y-%m-%d %H:%M:%S}',
            retain_last => 3
        )
        """
    ).show(truncate=False)
    spark.stop()


if __name__ == "__main__":
    main()
