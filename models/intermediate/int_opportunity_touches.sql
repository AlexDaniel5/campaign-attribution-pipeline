{#
  Build the ordered touch sequence for every opportunity.

  A "touch" is a campaign_member event belonging to the lead that
  converted into the opportunity's contact, dated on or before the
  opportunity's close date. Window functions assign each touch its
  position (touch_rank), the total number of touches on the
  opportunity, and the time from the touch to close (used by the
  time-decay model). This model is the shared input for all five
  attribution marts.
#}

with opportunities as (
    select
        opportunity_id,
        contact_id,
        amount_usd,
        created_date,
        close_date
    from {{ ref('stg_opportunities') }}
),

contacts as (
    select contact_id, lead_id
    from {{ ref('stg_contacts') }}
),

members as (
    select campaign_member_id, campaign_id, lead_id, touch_date
    from {{ ref('stg_campaign_members') }}
),

touches as (
    select
        o.opportunity_id,
        o.amount_usd,
        o.close_date,
        m.campaign_id,
        m.campaign_member_id,
        m.touch_date
    from opportunities o
    inner join contacts c on o.contact_id = c.contact_id
    inner join members  m on m.lead_id = c.lead_id
    where m.touch_date <= o.close_date
)

select
    opportunity_id,
    campaign_id,
    campaign_member_id,
    touch_date,
    amount_usd,
    row_number() over (
        partition by opportunity_id
        order by touch_date asc, campaign_member_id asc
    ) as touch_rank,
    count(*) over (partition by opportunity_id) as total_touches,
    date_diff('day', touch_date, close_date) as days_to_close
from touches
