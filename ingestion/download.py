"""Download TLC Parquet files and store them as is in the bronze bucket."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import boto3
import httpx
from botocore.exceptions import ClientError

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
SERVICES = ("yellow", "green", "fhvhv")
BUCKET = "bronze"


def parse_months(spec: str) -> list[str]:
    """Expand `2024-01..2024-03` or `2024-01,2024-05` to a sorted list of months."""
    months: set[str] = set()
    for part in spec.split(","):
        start, _, end = part.strip().partition("..")
        year, month = map(int, start.split("-"))
        last_year, last_month = map(int, (end or start).split("-"))
        if (last_year, last_month) < (year, month):
            raise ValueError(f"plage de mois inversée : {part}")
        while (year, month) <= (last_year, last_month):
            months.add(f"{year:04d}-{month:02d}")
            month += 1
            if month == 13:
                year, month = year + 1, 1
    return sorted(months)


def object_key(service: str, month: str) -> str:
    return f"{service}/month={month}/{service}_tripdata_{month}.parquet"


def source_url(service: str, month: str) -> str:
    return f"{BASE_URL}/{service}_tripdata_{month}.parquet"


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "lakeadmin"),
        aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "lakeadmin123"),
        region_name="us-east-1",
    )


def already_ingested(s3, key: str, expected_size: int) -> bool:
    """Idempotence: a complete object of the same size is not downloaded twice."""
    try:
        return s3.head_object(Bucket=BUCKET, Key=key)["ContentLength"] == expected_size
    except ClientError:
        return False


def ingest(s3, service: str, month: str, client: httpx.Client) -> str:
    url, key = source_url(service, month), object_key(service, month)
    head = client.head(url)
    head.raise_for_status()
    size = int(head.headers["content-length"])
    if already_ingested(s3, key, size):
        return "déjà présent"
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "file.parquet"
        with client.stream("GET", url) as response, path.open("wb") as target:
            response.raise_for_status()
            for chunk in response.iter_bytes(1 << 20):
                target.write(chunk)
        s3.upload_file(str(path), BUCKET, key)
    return f"ingéré ({size / 1e6:.0f} Mo)"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--months", required=True, help="2024-01..2024-03")
    parser.add_argument("--services", default=",".join(SERVICES))
    args = parser.parse_args()
    s3 = s3_client()
    with httpx.Client(timeout=300.0, follow_redirects=True) as client:
        for month in parse_months(args.months):
            for service in args.services.split(","):
                print(f"{service} {month} : {ingest(s3, service, month, client)}")


if __name__ == "__main__":
    main()
