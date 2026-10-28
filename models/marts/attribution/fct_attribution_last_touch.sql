{#
  Last-touch attribution: 100% of the credit goes to the final touch
  on each opportunity (touch_rank = total_touches). Credit is
  normalized so it sums to 1.0 per opportunity.
#}

with touches as (
    select * from {{ ref('int_opportunity_touches') }}
),

weighted as (
    select
        *,
        case when touch_rank = total_touches then 1.0 else 0.0 end as raw_weight
    from touches
),

credited as (
    select
        *,
        raw_weight
            / nullif(sum(raw_weight) over (partition by opportunity_id), 0)
            as credit
    from weighted
)

select
    opportunity_id,
    campaign_id,
    campaign_member_id,
    touch_date,
    touch_rank,
    total_touches,
    cast('last_touch' as varchar) as attribution_model,
    credit,
    credit * amount_usd as credited_amount
from credited
