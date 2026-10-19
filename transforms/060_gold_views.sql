-- gold schema: governed views over marts. consumers query these, not raw.
-- owner_email is masked outside sales_ops per governance/access_matrix.yaml.
create schema if not exists gold;

create or replace view gold.arr_bridge_monthly as
select * from marts.arr_bridge_monthly;

create or replace view gold.retention_cohorts as
select *, round(current_arr / nullif(cohort_start_arr, 0), 4) as nrr,
          round(grr_arr / nullif(cohort_start_arr, 0), 4) as grr
from marts.retention_cohorts;

create or replace view gold.unit_economics_monthly as
select * from marts.unit_economics_monthly;

create or replace view gold.account_health as
with latest as (
    select account_id, max(month) as month
    from marts.fct_arr_monthly
    where not is_churned
    group by account_id
),
usage as (
    select account_id, month,
           sum(active_users) as active_users,
           sum(event_count) as event_count
    from raw.product_events_monthly
    group by account_id, month
)
select
    a.account_id,
    a.account_name,
    a.segment,
    a.industry,
    a.region,
    -- PII policy: local part replaced with a stable hash
    'rep' || substr(md5(a.owner_email), 1, 6) || '@nimbus.example' as owner_email_masked,
    l.month as latest_month,
    f.arr_end as current_arr,
    u.active_users,
    u.event_count
from raw.crm_accounts a
join latest l using (account_id)
join marts.fct_arr_monthly f on f.account_id = a.account_id and f.month = l.month
left join usage u on u.account_id = a.account_id and u.month = l.month;

create or replace view gold.pipeline_funnel as
select segment, created_month,
       count(*) as opportunities,
       count(*) filter (where stage = 'Closed Won') as wins,
       round(avg(case when stage = 'Closed Won' then amount end), 0) as avg_deal_arr
from raw.crm_opportunities
group by segment, created_month;

create or replace view gold.feature_adoption as
select month, feature,
       sum(active_users) as active_users,
       sum(event_count) as event_count
from raw.product_events_monthly
group by month, feature;
