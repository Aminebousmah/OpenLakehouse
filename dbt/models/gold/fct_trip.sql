{{ config(properties={"partitioning": "ARRAY['month(pickup_date)']"}) }}

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
    duration_minutes
from {{ ref('stg_trips') }}
