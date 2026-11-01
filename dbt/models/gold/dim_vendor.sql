with vendors as (
    select distinct service, vendor_id from {{ ref('stg_trips') }}
)

select
    service,
    vendor_id,
    case vendor_id
        when '1' then 'Creative Mobile Technologies'
        when '2' then 'Curb Mobility'
        when '6' then 'Myle Technologies'
        when '7' then 'Helix'
        when 'HV0002' then 'Juno'
        when 'HV0003' then 'Uber'
        when 'HV0004' then 'Via'
        when 'HV0005' then 'Lyft'
        else 'Inconnu'
    end as vendor_name
from vendors
