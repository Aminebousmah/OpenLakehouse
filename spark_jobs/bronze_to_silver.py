"""Bronze to silver: clean, type, deduplicate, and unify yellow, green and fhvhv.

A month reloaded replaces its partitions (dynamic overwrite): rows are never doubled.
"""

from __future__ import annotations

import argparse
import calendar

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

TABLE = "lake.silver.trips"
COLUMNS = [
    "trip_id", "service", "vendor_id", "pickup_ts", "dropoff_ts", "pickup_zone_id",
    "dropoff_zone_id", "passenger_count", "trip_distance_miles", "payment_type", "fare_amount",
    "tip_amount", "total_amount", "duration_minutes", "source_month",
]
MAX_DURATION_MINUTES = 360
MAX_DISTANCE_MILES = 200


def read_yellow(spark: SparkSession, month: str) -> DataFrame:
    source = spark.read.parquet(f"s3a://bronze/yellow/month={month}/")
    return source.select(
        F.lit("yellow").alias("service"),
        F.col("VendorID").cast("string").alias("vendor_id"),
        F.col("tpep_pickup_datetime").alias("pickup_ts"),
        F.col("tpep_dropoff_datetime").alias("dropoff_ts"),
        F.col("PULocationID").cast("int").alias("pickup_zone_id"),
        F.col("DOLocationID").cast("int").alias("dropoff_zone_id"),
        F.col("passenger_count").cast("int").alias("passenger_count"),
        F.col("trip_distance").cast("double").alias("trip_distance_miles"),
        F.col("payment_type").cast("int").alias("payment_type"),
        F.col("fare_amount").cast("double").alias("fare_amount"),
        F.col("tip_amount").cast("double").alias("tip_amount"),
        F.col("total_amount").cast("double").alias("total_amount"),
    )


def read_green(spark: SparkSession, month: str) -> DataFrame:
    source = spark.read.parquet(f"s3a://bronze/green/month={month}/")
    return source.select(
        F.lit("green").alias("service"),
        F.col("VendorID").cast("string").alias("vendor_id"),
        F.col("lpep_pickup_datetime").alias("pickup_ts"),
        F.col("lpep_dropoff_datetime").alias("dropoff_ts"),
        F.col("PULocationID").cast("int").alias("pickup_zone_id"),
        F.col("DOLocationID").cast("int").alias("dropoff_zone_id"),
        F.col("passenger_count").cast("int").alias("passenger_count"),
        F.col("trip_distance").cast("double").alias("trip_distance_miles"),
        F.col("payment_type").cast("int").alias("payment_type"),
        F.col("fare_amount").cast("double").alias("fare_amount"),
        F.col("tip_amount").cast("double").alias("tip_amount"),
        F.col("total_amount").cast("double").alias("total_amount"),
    )


def read_fhvhv(spark: SparkSession, month: str) -> DataFrame:
    """Ride-hailing trips have no payment type, and their fare is split over several columns."""
    source = spark.read.parquet(f"s3a://bronze/fhvhv/month={month}/")
    total = (
        F.col("base_passenger_fare") + F.col("tolls") + F.col("bcf") + F.col("sales_tax")
        + F.col("congestion_surcharge") + F.col("tips")
    )
    return source.select(
        F.lit("fhvhv").alias("service"),
        F.col("hvfhs_license_num").alias("vendor_id"),
        F.col("pickup_datetime").alias("pickup_ts"),
        F.col("dropoff_datetime").alias("dropoff_ts"),
        F.col("PULocationID").cast("int").alias("pickup_zone_id"),
        F.col("DOLocationID").cast("int").alias("dropoff_zone_id"),
        F.lit(None).cast("int").alias("passenger_count"),
        F.col("trip_miles").cast("double").alias("trip_distance_miles"),
        F.lit(None).cast("int").alias("payment_type"),
        F.col("base_passenger_fare").cast("double").alias("fare_amount"),
        F.col("tips").cast("double").alias("tip_amount"),
        total.cast("double").alias("total_amount"),
    )


READERS = {"yellow": read_yellow, "green": read_green, "fhvhv": read_fhvhv}


def month_bounds(month: str) -> tuple[str, str]:
    year, number = map(int, month.split("-"))
    last = calendar.monthrange(year, number)[1]
    return f"{month}-01 00:00:00", f"{month}-{last:02d} 23:59:59"


def clean(trips: DataFrame, month: str) -> DataFrame:
    """Keep plausible trips of this month. TLC files contain stray rows from other years."""
    start, end = month_bounds(month)
    duration = F.expr("timestampdiff(SECOND, pickup_ts, dropoff_ts)") / 60
    first, last = F.lit(start).cast("timestamp_ntz"), F.lit(end).cast("timestamp_ntz")
    key_columns = ["service", "vendor_id", "pickup_ts", "dropoff_ts", "pickup_zone_id",
                   "dropoff_zone_id", "trip_distance_miles", "total_amount"]
    # Identical rows are duplicates: there is no natural trip identifier in the source.
    return (
        trips.withColumn("duration_minutes", duration)
        .filter(F.col("pickup_ts").between(first, last))
        .filter(F.col("duration_minutes").between(0, MAX_DURATION_MINUTES))
        .filter(F.col("trip_distance_miles").between(0, MAX_DISTANCE_MILES))
        .filter(F.col("total_amount") >= 0)
        .filter(F.col("pickup_zone_id").isNotNull() & F.col("dropoff_zone_id").isNotNull())
        .dropDuplicates(key_columns)
        .withColumn(
            "trip_id",
            F.sha2(F.concat_ws("|", *[F.col(c).cast("string") for c in key_columns]), 256),
        )
        .withColumn("source_month", F.lit(month))
        .select(*COLUMNS)
    )


CREATE_TABLE = f"""
create table if not exists {TABLE} (
    trip_id string,
    service string,
    vendor_id string,
    pickup_ts timestamp_ntz,
    dropoff_ts timestamp_ntz,
    pickup_zone_id int,
    dropoff_zone_id int,
    passenger_count int,
    trip_distance_miles double,
    payment_type int,
    fare_amount double,
    tip_amount double,
    total_amount double,
    duration_minutes double,
    source_month string
)
using iceberg
partitioned by (days(pickup_ts))
tblproperties (
    'format-version' = '2',
    'write.target-file-size-bytes' = '268435456',
    'write.distribution-mode' = 'hash'
)
"""


def run(month: str, services: list[str]) -> None:
    spark = SparkSession.builder.appName(f"bronze_to_silver_{month}").getOrCreate()
    spark.sql("create namespace if not exists lake.silver")
    spark.sql(CREATE_TABLE)
    frames = [READERS[service](spark, month) for service in services]
    union = frames[0]
    for frame in frames[1:]:
        union = union.unionByName(frame)
    clean(union, month).writeTo(TABLE).overwritePartitions()
    rows = spark.table(TABLE).filter(F.col("source_month") == month).count()
    print(f"{TABLE} {month} : {rows} lignes")
    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True)
    parser.add_argument("--services", default="yellow,green,fhvhv")
    args = parser.parse_args()
    run(args.month, args.services.split(","))


if __name__ == "__main__":
    main()
