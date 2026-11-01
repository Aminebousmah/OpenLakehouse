"""Benchmark queries. `{table}` is the trip table under test."""

QUERIES = {
    "monthly_aggregate": """
        select date_trunc('month', pickup_ts) as month, service, count(*) as trips,
               avg(total_amount) as avg_total
        from {table}
        group by 1, 2
    """,
    "single_day_filter": """
        select count(*) as trips, sum(total_amount) as revenue
        from {table}
        where pickup_ts >= timestamp '2024-02-14 00:00:00'
          and pickup_ts < timestamp '2024-02-15 00:00:00'
    """,
    "top_zones": """
        select pickup_zone_id, count(*) as trips
        from {table}
        where pickup_ts >= timestamp '2024-02-01 00:00:00'
          and pickup_ts < timestamp '2024-03-01 00:00:00'
        group by 1
        order by 2 desc
        limit 20
    """,
    "dimension_join": """
        select z.borough, avg(t.tip_amount) as avg_tip, count(*) as trips
        from {table} as t
        inner join iceberg.gold.dim_zone as z on t.pickup_zone_id = z.zone_id
        where t.pickup_ts >= timestamp '2024-02-01 00:00:00'
          and t.pickup_ts < timestamp '2024-03-01 00:00:00'
        group by 1
    """,
}
