with source as (
    select * from {{ source('raw', 'raw_campaigns') }}
)

select
    campaign_id,
    campaign_name,
    channel,
    campaign_type,
    cast(start_date as date) as start_date,
    cast(end_date as date)   as end_date,
    budget_usd,
    is_active
from source
