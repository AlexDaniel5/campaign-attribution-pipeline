{#
  Linear attribution: credit is split evenly across every touch on the
  opportunity (1 / total_touches). Normalization is explicit so the
  credit sums to 1.0 per opportunity.
#}

with touches as (
    select * from {{ ref('int_opportunity_touches') }}
),

weighted as (
    select
        *,
        1.0 as raw_weight
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
    cast('linear' as varchar) as attribution_model,
    credit,
    credit * amount_usd as credited_amount
from credited
