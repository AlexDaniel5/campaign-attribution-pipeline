{#
  Demand-generation funnel per campaign.

  For each campaign we count the distinct leads that are members of the
  campaign and the subset that reached each downstream stage:

      lead -> MQL -> opportunity -> closed-won

  plus the stage-to-stage conversion rates. Because the generator makes
  every converted lead an MQL, the counts are monotonically
  non-increasing (enforced by a singular test).
#}

with members as (
    select distinct campaign_id, lead_id
    from {{ ref('stg_campaign_members') }}
),

leads as (
    select lead_id, is_mql
    from {{ ref('stg_leads') }}
),

contacts as (
    select contact_id, lead_id
    from {{ ref('stg_contacts') }}
),

opportunities as (
    select opportunity_id, contact_id, is_won
    from {{ ref('stg_opportunities') }}
),

lead_outcomes as (
    select
        m.campaign_id,
        m.lead_id,
        max(case when l.is_mql then 1 else 0 end)                          as reached_mql,
        max(case when o.opportunity_id is not null then 1 else 0 end)      as reached_opp,
        max(case when o.is_won then 1 else 0 end)                          as reached_won
    from members m
    inner join leads l on m.lead_id = l.lead_id
    left join contacts c on c.lead_id = l.lead_id
    left join opportunities o on o.contact_id = c.contact_id
    group by m.campaign_id, m.lead_id
),

funnel as (
    select
        campaign_id,
        count(*)            as leads_count,
        sum(reached_mql)    as mql_count,
        sum(reached_opp)    as opportunity_count,
        sum(reached_won)    as won_count
    from lead_outcomes
    group by campaign_id
)

select
    c.campaign_id,
    c.campaign_name,
    c.channel,
    c.campaign_type,
    f.leads_count,
    f.mql_count,
    f.opportunity_count,
    f.won_count,
    round(f.mql_count * 1.0 / nullif(f.leads_count, 0), 4)        as lead_to_mql_rate,
    round(f.opportunity_count * 1.0 / nullif(f.mql_count, 0), 4)  as mql_to_opp_rate,
    round(f.won_count * 1.0 / nullif(f.opportunity_count, 0), 4)  as opp_to_won_rate,
    round(f.won_count * 1.0 / nullif(f.leads_count, 0), 4)        as lead_to_won_rate
from funnel f
inner join {{ ref('stg_campaigns') }} c on f.campaign_id = c.campaign_id
