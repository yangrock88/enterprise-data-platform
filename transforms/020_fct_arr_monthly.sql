-- account x month ARR state: beginning balance, movements, ending balance.
-- the spine for retention math and the ARR bridge.
create or replace table marts.fct_arr_monthly as
with months as (
    select distinct cast(month as date) as month from raw.billing_arr_movements
),
first_seen as (
    select account_id, min(cast(month as date)) as first_month
    from raw.billing_arr_movements
    group by account_id
),
grid as (
    select f.account_id, m.month
    from first_seen f
    join months m on m.month >= f.first_month
),
movements as (
    select account_id, month, sum(arr_change) as net_change,
           sum(case when movement = 'churn' then 1 else 0 end) as churned_flag
    from raw.billing_arr_movements
    group by account_id, month
),
assembled as (
    select
        g.account_id,
        g.month,
        coalesce(m.net_change, 0) as net_change,
        coalesce(m.churned_flag, 0) as churned_flag
    from grid g
    left join movements m using (account_id, month)
),
running as (
    select
        account_id, month, net_change, churned_flag,
        sum(net_change) over (
            partition by account_id order by month
            rows between unbounded preceding and current row
        ) as arr_end
    from assembled
)
select
    account_id,
    month,
    arr_end - net_change as arr_begin,
    net_change,
    arr_end,
    case when churned_flag = 1 or arr_end <= 0 then true else false end as is_churned
from running
