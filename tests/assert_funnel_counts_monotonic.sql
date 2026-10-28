-- The demand-generation funnel must be monotonically non-increasing:
-- leads >= MQLs >= opportunities >= closed-won for every campaign.
select
    campaign_id,
    leads_count,
    mql_count,
    opportunity_count,
    won_count
from {{ ref('fct_campaign_funnel') }}
where leads_count < mql_count
   or mql_count < opportunity_count
   or opportunity_count < won_count
