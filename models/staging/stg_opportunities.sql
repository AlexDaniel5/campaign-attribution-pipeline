with source as (
    select * from {{ source('raw', 'raw_opportunities') }}
)

select
    opportunity_id,
    contact_id,
    opportunity_name,
    stage,
    amount_usd,
    cast(created_date as date) as created_date,
    cast(close_date as date)   as close_date,
    is_closed,
    is_won
from source
