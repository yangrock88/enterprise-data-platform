-- NRR / GRR by monthly cohort, the retention table investors ask for.
-- NRR counts expansion; GRR caps recovery at the cohort's starting ARR.
create or replace table marts.retention_cohorts as
with cohorts as (
    select account_id, min(month) as cohort_month
    from marts.fct_arr_monthly
    group by account_id
),
base as (
    select c.account_id, c.cohort_month, a.month, a.arr_begin, a.arr_end
    from cohorts c
    join marts.fct_arr_monthly a using (account_id)
    where a.month > c.cohort_month
),
starting as (
    select account_id, cohort_month,
           max(case when month = cohort_month then arr_end end) as cohort_start_arr
    from (
        select account_id, month, arr_end,
               min(month) over (partition by account_id) as cohort_month
        from marts.fct_arr_monthly
    ) t
    group by account_id, cohort_month
)
select
    s.cohort_month,
    datediff('month', s.cohort_month, b.month) as months_since_start,
    sum(s.cohort_start_arr) as cohort_start_arr,
    sum(b.arr_end) as current_arr,
    sum(greatest(least(b.arr_end, s.cohort_start_arr), 0)) as grr_arr,
    count(distinct b.account_id) as live_accounts
from starting s
join base b using (account_id, cohort_month)
group by s.cohort_month, b.month
order by s.cohort_month, b.month
