with source as (
    select * from {{ source('raw', 'raw_campaign_members') }}
)

select
    campaign_member_id,
    campaign_id,
    lead_id,
    member_status,
    is_responded,
    cast(touch_date as date) as touch_date
from source
