with bounds as (
    select min(pickup_date) as first_date, max(pickup_date) as last_date
    from {{ ref('stg_trips') }}
),

days as (
    select day_value
    from bounds
    cross join unnest(sequence(first_date, last_date, interval '1' day)) as t (day_value)
)

select
    day_value as date_day,
    year(day_value) as year_number,
    month(day_value) as month_number,
    day_of_week(day_value) as iso_day_of_week,
    day_of_week(day_value) >= 6 as is_weekend
from days
