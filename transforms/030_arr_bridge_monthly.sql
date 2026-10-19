-- company-level monthly ARR bridge: beginning ARR + new + expansion
-- - contraction - churn = ending ARR. the chart every board deck needs.
create or replace table marts.arr_bridge_monthly as
with classified as (
    select
        month,
        sum(case when movement = 'new' then arr_change else 0 end) as new_arr,
        sum(case when movement = 'expansion' then arr_change else 0 end) as expansion_arr,
        sum(case when movement = 'contraction' then -arr_change else 0 end) as contraction_arr,
        sum(case when movement = 'churn' then -arr_change else 0 end) as churned_arr
    from raw.billing_arr_movements
    group by month
),
running as (
    select
        month, new_arr, expansion_arr, contraction_arr, churned_arr,
        sum(new_arr + expansion_arr - contraction_arr - churned_arr)
            over (order by month rows between unbounded preceding and current row)
            as arr_end
    from classified
)
select
    month,
    arr_end - (new_arr + expansion_arr - contraction_arr - churned_arr) as arr_begin,
    new_arr,
    expansion_arr,
    contraction_arr,
    churned_arr,
    arr_end
from running
order by month
