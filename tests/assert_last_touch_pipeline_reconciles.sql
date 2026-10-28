-- Total credited amount must reconcile to total opportunity pipeline.
with credited as (
    select sum(credited_amount) as total_credited
    from {{ ref('fct_attribution_last_touch') }}
),
pipeline as (
    select sum(amount_usd) as total_pipeline
    from {{ ref('stg_opportunities') }}
)
select
    credited.total_credited,
    pipeline.total_pipeline
from credited
cross join pipeline
where abs(credited.total_credited - pipeline.total_pipeline) > 0.01
