with source as (
    select * from {{ source('raw', 'raw_contacts') }}
)

select
    contact_id,
    lead_id,
    first_name,
    last_name,
    email,
    company,
    title,
    cast(created_date as date) as created_date
from source
