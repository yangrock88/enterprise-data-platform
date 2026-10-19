-- normalized ARR movement ledger, one row per account x month x movement
create or replace table marts.fct_arr_movements as
select
    account_id,
    cast(month as date) as month,
    movement,
    arr_change
from raw.billing_arr_movements
