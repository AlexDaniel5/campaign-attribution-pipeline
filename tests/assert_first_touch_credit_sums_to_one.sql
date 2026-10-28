-- Credit must sum to exactly 1.0 across the touches of every opportunity.
-- The test fails if any opportunity's total credit deviates from 1.0.
select
    opportunity_id,
    sum(credit) as total_credit
from {{ ref('fct_attribution_first_touch') }}
group by opportunity_id
having abs(sum(credit) - 1.0) > 1e-6
