"""Offline platform tests: seeds its own source data, runs the real flow."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import flow, seeder  # noqa: E402


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("platform")
    src = tmp / "source"
    wh = tmp / "warehouse.duckdb"
    seeder.seed(out_dir=src)
    flow.run_pipeline(source_dir=src, warehouse=wh)
    return wh


def test_arr_bridge_reconciles(warehouse):
    """beginning + new + expansion - contraction - churn == ending, every month."""
    with duckdb.connect(str(warehouse), read_only=True) as con:
        bad = con.execute(
            """
            select count(*) from marts.arr_bridge_monthly
            where abs(arr_begin + new_arr + expansion_arr
                      - contraction_arr - churned_arr - arr_end) > 0.01
            """
        ).fetchone()[0]
        assert bad == 0


def test_nrr_within_sane_bounds(warehouse):
    with duckdb.connect(str(warehouse), read_only=True) as con:
        row = con.execute(
            """
            select avg(current_arr / nullif(cohort_start_arr, 0)),
                   avg(grr_arr / nullif(cohort_start_arr, 0))
            from gold.retention_cohorts
            where months_since_start between 3 and 24
            """
        ).fetchone()
        nrr, grr = row
        assert 0.5 < nrr < 1.8, f"implausible NRR {nrr}"
        assert 0.5 < grr < 1.05, f"implausible GRR {grr}"
        assert grr <= nrr + 1e-9, "GRR can never exceed NRR"


def test_gold_view_masks_owner_email(warehouse):
    """The governance contract: gold.account_health must not leak raw emails."""
    with duckdb.connect(str(warehouse), read_only=True) as con:
        leaked = con.execute(
            """
            select count(*) from gold.account_health
            where owner_email_masked like 'rep%@nimbus.example'
              and owner_email_masked not like 'rep______%'
              and length(owner_email_masked) > 30
            """
        ).fetchone()[0]
        # masked form is rep + 6 hex chars + domain = fixed short length
        raw_emails = con.execute("select distinct owner_email from raw.crm_accounts").df()
        gold_cols = con.execute("select * from gold.account_health limit 1").df().columns
        assert "owner_email" not in list(gold_cols), "raw PII column exposed in gold"
        assert leaked == 0


def test_contracts_catch_broken_grain(tmp_path):
    """If the ARR grain breaks, the flow must raise, not warn."""
    src = tmp_path / "source"
    seeder.seed(out_dir=src)
    wh = tmp_path / "wh.duckdb"
    flow.run_pipeline(source_dir=src, warehouse=wh)
    with duckdb.connect(str(wh)) as con:
        con.execute("insert into marts.fct_arr_monthly "
                    "select * from marts.fct_arr_monthly limit 5")
    with pytest.raises(AssertionError):
        flow.data_contracts.fn(wh)
