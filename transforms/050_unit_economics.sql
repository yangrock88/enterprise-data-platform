-- monthly go-to-market efficiency: CAC, magic number, payback proxy.
create or replace table marts.unit_economics_monthly as
with new_arr as (
    select month, sum(arr_change) as new_business_arr
    from raw.billing_arr_movements
    where movement in ('new', 'expansion')
    group by month
),
logos as (
    select month, count(*) as new_logos
    from raw.billing_arr_movements
    where movement = 'new'
    group by month
)
select
    s.month,
    s.marketing_spend + s.sales_cost as sm_spend,
    coalesce(l.new_logos, 0) as new_logos,
    coalesce(n.new_business_arr, 0) as new_business_arr,
    case when coalesce(l.new_logos, 0) > 0
         then (s.marketing_spend + s.sales_cost) / l.new_logos end as cac,
    -- magic number: annualized net new ARR / prior-quarter S&M (approx monthly)
    case when s.marketing_spend + s.sales_cost > 0
         then coalesce(n.new_business_arr, 0) / (s.marketing_spend + s.sales_cost)
         end as magic_number_proxy
from raw.finance_sm_spend s
left join new_arr n using (month)
left join logos l using (month)
order by s.month
