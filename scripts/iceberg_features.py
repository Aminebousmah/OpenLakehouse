"""Demonstrate the Iceberg features on a small copy of silver, and record what really happens."""

from __future__ import annotations

import os
from pathlib import Path

import trino

TABLE = "iceberg.demo.trips"
OUT = Path(__file__).resolve().parent.parent / "docs" / "iceberg_features_results.md"


def main() -> None:
    connection = trino.dbapi.connect(
        host=os.environ.get("TRINO_HOST", "localhost"), port=8080, user="engineer"
    )
    cursor = connection.cursor()

    def run(sql: str) -> list:
        cursor.execute(sql)
        return cursor.fetchall()

    def one(sql: str):
        return run(sql)[0][0]

    run("create schema if not exists iceberg.demo")
    run(f"drop table if exists {TABLE}")
    run(
        f"""
        create table {TABLE} with (partitioning = array['month(pickup_ts)']) as
        select trip_id, service, pickup_ts, total_amount, tip_amount
        from iceberg.silver.trips
        where pickup_ts >= timestamp '2024-01-01 00:00:00'
          and pickup_ts < timestamp '2024-01-03 00:00:00'
        """
    )
    lines = ["# Fonctionnalités Iceberg : résultats mesurés", ""]
    rows = one(f"select count(*) from {TABLE}")
    first_total = one(f"select round(sum(total_amount), 2) from {TABLE}")
    first_snapshot = one(
        'select snapshot_id from iceberg.demo."trips$snapshots" order by committed_at limit 1'
    )
    lines += [f"Table de démonstration : {rows:,} trajets du 1er et du 2 janvier 2024.", ""]

    run(
        f"""
        merge into {TABLE} as target
        using (select trip_id from {TABLE} where service = 'green') as fixes
        on target.trip_id = fixes.trip_id
        when matched then update set total_amount = target.total_amount + 1
        """
    )
    corrected = one(f"select count(*) from {TABLE} where service = 'green'")
    after_merge = one(f"select round(sum(total_amount), 2) from {TABLE}")
    lines += [
        "## `MERGE INTO`",
        f"{corrected:,} lignes corrigées de +1 $. Total : {first_total:,} $ devenu "
        f"{after_merge:,} $.",
        "",
    ]

    before = one(
        f"select round(sum(total_amount), 2) from {TABLE} for version as of {first_snapshot}"
    )
    lines += [
        "## Time travel",
        f"Lecture du premier snapshot après la correction : {before:,} $, soit le total d'origine "
        f"({'identique' if before == first_total else 'différent'}).",
        "",
    ]

    files_before = {row[0] for row in run('select file_path from iceberg.demo."trips$files"')}
    run(f"alter table {TABLE} add column review_flag boolean")
    files_after = {row[0] for row in run('select file_path from iceberg.demo."trips$files"')}
    nulls = one(f"select count(*) from {TABLE} where review_flag is null")
    lines += [
        "## Évolution de schéma",
        f"Colonne ajoutée. Fichiers réécrits : {len(files_after - files_before)}. "
        f"Les {nulls:,} lignes existantes lisent la nouvelle colonne à `null`.",
        "",
    ]

    run(f"alter table {TABLE} set properties partitioning = array['day(pickup_ts)']")
    run(
        f"""
        insert into {TABLE} (trip_id, service, pickup_ts, total_amount, tip_amount)
        select trip_id, service, pickup_ts + interval '31' day, total_amount, tip_amount
        from {TABLE} limit 1000
        """
    )
    monthly, daily = run(
        "select count_if(file_path like '%pickup_ts_month=%'), "
        "count_if(file_path like '%pickup_ts_day=%') from iceberg.demo.\"trips$files\""
    )[0]
    described = f"{monthly} fichier(s) restent partitionnés par mois, {daily} le sont par jour"
    lines += [
        "## Évolution de partition",
        f"Passage de `month` à `day`, sans réécrire l'existant. {described}.",
        "",
    ]

    snapshots_before = one('select count(*) from iceberg.demo."trips$snapshots"')
    run(f"alter table {TABLE} execute expire_snapshots(retention_threshold => '0s')")
    snapshots_after = one('select count(*) from iceberg.demo."trips$snapshots"')
    lines += [
        "## Expiration des snapshots",
        f"{snapshots_before} snapshots avant, {snapshots_after} après.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
