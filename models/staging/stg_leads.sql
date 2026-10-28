with source as (
    select * from {{ source('raw', 'raw_leads') }}
)

select
    lead_id,
    first_name,
    last_name,
    email,
    company,
    title,
    lead_source,
    cast(created_date as date)   as created_date,
    lead_status,
    is_mql,
    cast(mql_date as date)       as mql_date,
    is_converted,
    cast(converted_date as date) as converted_date,
    converted_contact_id
from source
