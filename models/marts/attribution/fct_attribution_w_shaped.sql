{#
  W-shaped attribution: the three anchor touches -- first, middle, and
  last -- each receive a heavy weight (3), while all other touches get
  a light weight (1). Normalizing by the per-opportunity sum of weights
  yields the classic ~30/30/30 split across the anchors (with the
  remainder shared by the middle touches) and guarantees credit sums to
  1.0. For opportunities with 1 or 2 touches the anchors collapse onto
  the same touches and normalization still holds.
#}

with touches as (
    select * from {{ ref('int_opportunity_touches') }}
),

anchored as (
    select
        *,
        cast(round((total_touches + 1) / 2.0) as integer) as middle_rank
    from touches
),

weighted as (
    select
        *,
        case
            when touch_rank in (1, total_touches, middle_rank) then 3.0
            else 1.0
        end as raw_weight
    from anchored
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
    cast('w_shaped' as varchar) as attribution_model,
    credit,
    credit * amount_usd as credited_amount
from credited
