with bounds as (
    select min(pickup_date) as first_date, max(pickup_date) as last_date
    from {{ ref('stg_trips') }}
),

days as (
    {{ select_days('first_date', 'last_date', 'bounds') }}
)

select
    day_value as date_day,
    year(day_value) as year_number,
    month(day_value) as month_number,
    {{ iso_day_of_week('day_value') }} as iso_day_of_week,
    {{ iso_day_of_week('day_value') }} >= 6 as is_weekend
from days
