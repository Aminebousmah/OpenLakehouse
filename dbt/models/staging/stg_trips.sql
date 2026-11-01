select
    trip_id,
    service,
    vendor_id,
    pickup_ts,
    dropoff_ts,
    cast(pickup_ts as date) as pickup_date,
    pickup_zone_id,
    dropoff_zone_id,
    passenger_count,
    trip_distance_miles,
    coalesce(payment_type, 0) as payment_type,
    fare_amount,
    tip_amount,
    total_amount,
    duration_minutes,
    source_month
from {{ source('silver', 'trips') }}
