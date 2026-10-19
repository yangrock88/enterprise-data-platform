"""Generate the synthetic source systems: CRM accounts/opportunities,
billing subscriptions (monthly ARR movements), product telemetry, and S&M spend.

Outputs 'raw' CSVs under data/source/ that the Prefect flow then ingests --
the same shape as exporting from Salesforce/Stripe/a product DB.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG = PROJECT_ROOT / "config" / "business.yaml"
SOURCE_DIR = PROJECT_ROOT / "data" / "source"


def month_range(n_months: int) -> pd.DatetimeIndex:
    return pd.date_range("2023-01-01", periods=n_months, freq="MS")


def seed(config_path: Path = CONFIG, out_dir: Path = SOURCE_DIR) -> None:
    cfg = yaml.safe_load(config_path.read_text())
    rng = np.random.default_rng(cfg["company"]["seed"])
    months = month_range(cfg["company"]["months_of_history"])
    n_months = len(months)

    seg_cfg = cfg["accounts"]["segments"]
    segments = list(seg_cfg.keys())
    seg_weights = np.array([seg_cfg[s]["weight"] for s in segments])
    seg_weights /= seg_weights.sum()

    accounts = []
    subscriptions = []
    opportunities = []
    events = []
    spend = []

    next_acct = 1

    def add_account(start_idx: int) -> dict:
        nonlocal next_acct
        seg = rng.choice(segments, p=seg_weights)
        lo, hi = seg_cfg[seg]["arr_floor"], seg_cfg[seg]["arr_ceiling"]
        arr = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
        acct = {
            "account_id": f"A{next_acct:05d}",
            "account_name": f"Customer {next_acct:04d}",
            "segment": seg,
            "industry": rng.choice(cfg["accounts"]["industries"]),
            "region": rng.choice(cfg["accounts"]["regions"]),
            "owner_email": f"rep{rng.integers(1, 24)}@nimbus.example",
            "created_month": months[start_idx],
            "arr": round(arr, 0),
        }
        next_acct += 1
        accounts.append(acct)
        return acct

    live: list[dict] = []
    for _ in range(cfg["accounts"]["starting_customers"]):
        acct = add_account(0)
        live.append(acct)
        # the opening book enters the ledger too, or balances go negative
        subscriptions.append({
            "account_id": acct["account_id"], "month": months[0],
            "movement": "new", "arr_change": acct["arr"],
        })

    motion = cfg["revenue_motion"]
    sales = cfg["sales"]
    new_logos = motion["new_logos_per_month"]["start"]
    mkt_spend = sales["marketing_spend_per_month"]["start"]
    sales_cost = sales["sales_headcount_cost_per_month"]["start"]

    for m_idx, month in enumerate(months):
        if m_idx > 0:
            new_logos *= 1 + motion["new_logos_per_month"]["growth"]
            mkt_spend *= 1 + sales["marketing_spend_per_month"]["growth"]
            sales_cost *= 1 + sales["sales_headcount_cost_per_month"]["growth"]

        spend.append({"month": month, "marketing_spend": round(mkt_spend, 0),
                      "sales_cost": round(sales_cost, 0)})

        # new logos + their opportunities (won)
        for _ in range(int(round(new_logos))):
            acct = add_account(m_idx)
            live.append(acct)
            subscriptions.append({
                "account_id": acct["account_id"], "month": month,
                "movement": "new", "arr_change": acct["arr"],
            })
            opportunities.append({
                "opportunity_id": f"O{len(opportunities):06d}",
                "account_id": acct["account_id"], "segment": acct["segment"],
                "created_month": month, "closed_month": month,
                "stage": "Closed Won", "amount": acct["arr"],
            })
            # lost pipeline around each win
            for _ in range(int(sales["pipeline_per_new_logo"]) - 1):
                opportunities.append({
                    "opportunity_id": f"O{len(opportunities):06d}",
                    "account_id": acct["account_id"], "segment": acct["segment"],
                    "created_month": month, "closed_month": month,
                    "stage": "Closed Lost",
                    "amount": round(acct["arr"] * rng.uniform(0.5, 1.5), 0),
                })

        # revenue motions on the existing book
        still_live = []
        for acct in live:
            if acct["created_month"] >= month and m_idx > 0:
                still_live.append(acct)
                continue
            seg = acct["segment"]
            r = rng.random()
            churn = motion["gross_churn_rate"][seg]
            expand = motion["expansion_rate"][seg]
            contract = motion["contraction_rate"][seg]
            if r < churn:
                subscriptions.append({
                    "account_id": acct["account_id"], "month": month,
                    "movement": "churn", "arr_change": -acct["arr"],
                })
                acct["arr"] = 0.0
                continue
            elif r < churn + expand:
                # round before applying: the in-memory balance must match the
                # ledger exactly, or churn postings drift by rounding dust
                delta = round(acct["arr"] * rng.uniform(*motion["expansion_size_pct"]), 0)
                acct["arr"] += delta
                subscriptions.append({
                    "account_id": acct["account_id"], "month": month,
                    "movement": "expansion", "arr_change": delta,
                })
            elif r < churn + expand + contract:
                delta = round(acct["arr"] * rng.uniform(*motion["contraction_size_pct"]), 0)
                acct["arr"] -= delta
                subscriptions.append({
                    "account_id": acct["account_id"], "month": month,
                    "movement": "contraction", "arr_change": -delta,
                })
            still_live.append(acct)
        live = [a for a in still_live if a["arr"] > 0]

        # product telemetry per live account
        for acct in live:
            health = rng.uniform(*cfg["product"]["dau_mau_ratio"])
            seats = max(2, int(acct["arr"] / 1200))
            mau = seats * rng.uniform(*cfg["product"]["seats_utilization"])
            for feat in cfg["product"]["features"]:
                adoption = rng.beta(2, 3) * health * 2
                events.append({
                    "account_id": acct["account_id"], "month": month,
                    "feature": feat,
                    "active_users": max(1, int(mau * min(adoption, 1))),
                    "event_count": int(mau * health * rng.uniform(20, 60)),
                })

    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(accounts).drop(columns=["arr"]).to_csv(
        out_dir / "crm_accounts.csv", index=False)
    pd.DataFrame(opportunities).to_csv(out_dir / "crm_opportunities.csv", index=False)
    pd.DataFrame(subscriptions).to_csv(out_dir / "billing_arr_movements.csv", index=False)
    pd.DataFrame(events).to_csv(out_dir / "product_events_monthly.csv", index=False)
    pd.DataFrame(spend).to_csv(out_dir / "finance_sm_spend.csv", index=False)
    print(f"seeded {len(accounts):,} accounts, {len(subscriptions):,} ARR movements, "
          f"{len(opportunities):,} opportunities, {len(events):,} telemetry rows")


if __name__ == "__main__":
    seed()
