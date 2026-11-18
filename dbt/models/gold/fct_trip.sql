{#
    Incremental by source month: a run deletes the month it reloads, then inserts it again.
    Rerunning a month, after a retry or a TLC correction, never duplicates a row.
#}
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='source_month',
        on_schema_change='fail',
        properties={"partitioning": "ARRAY['month(pickup_date)']"},
    )
}}

select
    trip_id,
    service,
    vendor_id,
    pickup_date,
    pickup_ts,
    dropoff_ts,
    pickup_zone_id,
    dropoff_zone_id,
    payment_type,
    passenger_count,
    trip_distance_miles,
    fare_amount,
    tip_amount,
    total_amount,
    duration_minutes,
    source_month
from {{ ref('stg_trips') }}
{% if is_incremental() %}
where {{ month_to_load_filter() }}
{% endif %}
