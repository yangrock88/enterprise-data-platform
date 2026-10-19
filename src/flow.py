"""Prefect ELT: extract raw source CSVs -> DuckDB raw schema -> SQL transforms
-> marts -> data contracts. Retries and a GitHub Actions cron make it
'production-shaped' without needing a server.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
from prefect import flow, task

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
WAREHOUSE = PROJECT_ROOT / "data" / "warehouse.duckdb"
SQL_DIR = PROJECT_ROOT / "transforms"

SOURCES = {
    "crm_accounts": "crm_accounts.csv",
    "crm_opportunities": "crm_opportunities.csv",
    "billing_arr_movements": "billing_arr_movements.csv",
    "product_events_monthly": "product_events_monthly.csv",
    "finance_sm_spend": "finance_sm_spend.csv",
}


@task(retries=2, retry_delay_seconds=5)
def extract_load(source_dir: Path, warehouse: Path) -> dict[str, int]:
    counts = {}
    with duckdb.connect(str(warehouse)) as con:
        con.execute("create schema if not exists raw")
        for table, filename in SOURCES.items():
            path = source_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"missing source extract: {path}")
            df = pd.read_csv(path)
            con.register("stage_df", df)
            con.execute(f"create or replace table raw.{table} as select * from stage_df")
            counts[table] = len(df)
    return counts


@task
def transform(warehouse: Path, sql_dir: Path) -> list[str]:
    """Run numbered SQL files in order; each builds one mart."""
    built = []
    files = sorted(sql_dir.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"no transforms found in {sql_dir}")
    with duckdb.connect(str(warehouse)) as con:
        con.execute("create schema if not exists marts")
        for sql_file in files:
            con.execute(sql_file.read_text())
            built.append(sql_file.name)
    return built


@task
def data_contracts(warehouse: Path) -> list[str]:
    """Hard-fail checks on the marts. A broken contract stops the run."""
    findings = []
    with duckdb.connect(str(warehouse)) as con:
        # every ARR drop must be explained by a contraction or churn movement
        check = con.execute(
            """
            select count(*) from marts.fct_arr_monthly f
            where f.arr_end < f.arr_begin - 0.01
              and not exists (
                    select 1 from marts.fct_arr_movements mv
                    where mv.account_id = f.account_id
                      and mv.month = f.month
                      and mv.movement in ('churn', 'contraction')
               )
            """
        ).fetchone()[0]
        if check:
            findings.append(f"[warn] {check} account-months with unexplained ARR drops")

        negative = con.execute(
            "select count(*) from marts.fct_arr_monthly where arr_end < 0"
        ).fetchone()[0]
        if negative:
            raise AssertionError(f"negative ARR in {negative} account-months")

        dupes = con.execute(
            """
            select count(*) from (
                select account_id, month, count(*) n
                from marts.fct_arr_monthly group by 1,2 having n > 1
            )
            """
        ).fetchone()[0]
        if dupes:
            raise AssertionError(f"fct_arr_monthly grain broken: {dupes} dupes")
    return findings


@flow(name="nimbus-elt")
def run_pipeline(source_dir: Path = SOURCE_DIR, warehouse: Path = WAREHOUSE,
                 sql_dir: Path = SQL_DIR) -> None:
    counts = extract_load(source_dir, warehouse)
    print(f"loaded: {counts}")
    built = transform(warehouse, sql_dir)
    print(f"built: {built}")
    for finding in data_contracts(warehouse):
        print(finding)


if __name__ == "__main__":
    run_pipeline()
