-- Credit must sum to exactly 1.0 across the touches of every opportunity.
select
    opportunity_id,
    sum(credit) as total_credit
from {{ ref('fct_attribution_w_shaped') }}
group by opportunity_id
having abs(sum(credit) - 1.0) > 1e-6
