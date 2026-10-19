# Enterprise Analytics Platform — SaaS Revenue Intelligence

A production-shaped analytics platform for a synthetic B2B SaaS company
("Nimbus Analytics"): Prefect-orchestrated ELT into DuckDB, SQL-built revenue
marts, a governed gold layer with PII masking, and data contracts that stop
the pipeline when reality breaks the model.

## Architecture

```
data/source/                 synthetic source systems (seeded, reproducible)
  crm_accounts.csv           -- "Salesforce"
  crm_opportunities.csv
  billing_arr_movements.csv  -- "Stripe/Zuora" ARR movement ledger
  product_events_monthly.csv -- product telemetry
  finance_sm_spend.csv       -- S&M spend

        |  python run.py etl   (Prefect flow: extract_load -> transform -> contracts)
        v

warehouse.duckdb
  raw.*                      landed source data
  marts.*                    SQL transforms (transforms/*.sql, numbered, in order)
    fct_arr_monthly          account x month ARR state (grain-checked)
    arr_bridge_monthly       new/expansion/contraction/churn bridge
    retention_cohorts        NRR/GRR by cohort
    unit_economics_monthly   CAC, magic number
  gold.*                     governed views; owner_email masked per
                             governance/access_matrix.yaml
```

## Run it

```bat
python run.py all    :: seed -> etl (contracts enforced)
pytest tests -q      :: incl. a test that BREAKS a mart and proves the contract fires
python run.py dashboard
```

## The governance story

- **Contracts, not hope**: negative ARR, broken grains, and unreconciled drops
  hard-fail the flow. During development the negative-ARR contract caught a
  real source bug (rounding drift between the ledger and in-memory balances) —
  that is the point of having them.
- **PII masking by view**: consumers query `gold.*`, never `raw.*`; the access
  matrix is versioned in `governance/access_matrix.yaml`, and a test asserts
  raw owner emails cannot leak through the gold views.
- **Every number reproducible**: `python run.py all` regenerates the whole
  platform from the seed.

## Known simplifications (called out on purpose)

- DuckDB has no server-side RBAC; governance is enforced as contracted views
  plus tests, which is exactly how you'd prototype it before a warehouse GRANT
  migration.
- Magic number is computed monthly rather than on the classic quarterly lag.
