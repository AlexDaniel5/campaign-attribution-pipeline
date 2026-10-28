{#
  Time-decay attribution: touches closer to the opportunity close date
  earn exponentially more credit, using a 7-day half-life. The raw
  weight for a touch is 2 ^ (-days_to_close / 7); dividing by the
  per-opportunity sum of weights normalizes credit to 1.0.
#}

{% set half_life_days = 7 %}

with touches as (
    select * from {{ ref('int_opportunity_touches') }}
),

weighted as (
    select
        *,
        power(2.0, -1.0 * days_to_close / {{ half_life_days }}.0) as raw_weight
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
    cast('time_decay' as varchar) as attribution_model,
    credit,
    credit * amount_usd as credited_amount
from credited
