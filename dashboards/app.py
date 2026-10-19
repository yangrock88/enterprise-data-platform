"""SaaS executive metrics: ARR bridge, retention, go-to-market efficiency."""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import theme

ACCENT = "#0891b2"  # cyan
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = PROJECT_ROOT / "data" / "warehouse.duckdb"

st.set_page_config(page_title="Nimbus — Revenue Intelligence", layout="wide")
theme.apply(ACCENT)


@st.cache_data(ttl=3600)
def query(sql: str) -> pd.DataFrame:
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        return con.execute(sql).df()


def main() -> None:
    bridge = query("select * from gold.arr_bridge_monthly order by month")
    bridge["month"] = bridge["month"].astype("datetime64[ns]")
    latest = bridge.iloc[-1]
    yoy = bridge["arr_end"].iloc[-1] / bridge["arr_end"].iloc[-13] - 1
    live = query(
        "select count(distinct account_id) n from marts.fct_arr_monthly "
        "where arr_end > 0"
    ).iloc[0, 0]
    cohorts = query(
        """
        select months_since_start, avg(nrr) as nrr, avg(grr) as grr
        from gold.retention_cohorts
        where months_since_start between 1 and 24
        group by 1 order by 1
        """
    )
    ue = query("select * from gold.unit_economics_monthly order by month")
    ue["month"] = ue["month"].astype("datetime64[ns]")
    mature = cohorts[cohorts["months_since_start"].between(6, 18)]
    avg_nrr = mature["nrr"].mean()

    # ---- hero -------------------------------------------------------------
    theme.hero(
        "Revenue Intelligence — Nimbus Analytics",
        [
            ("ARR", f"${latest['arr_end'] / 1e6:,.1f}M",
             "Annual recurring revenue at month end."),
            ("YoY growth", f"{yoy:.0%}",
             "Ending ARR versus the same month one year ago."),
            ("Mature-cohort NRR", f"{avg_nrr:.1%}",
             "Net revenue retention, cohorts 6–18 months old: expansion minus contraction and churn."),
            ("Live customers", f"{int(live):,}",
             "Accounts with positive ARR right now."),
        ],
        ACCENT,
    )

    theme.guide_bar(
        {
            "problem": "A subscription business can grow fast and still be "
                       "dying \u2014 growth bought with marketing dollars while "
                       "the existing base churns is a treadmill, not a "
                       "business. This dashboard answers two questions at "
                       "once: is growth efficient, and is it durable?",
            "approach": "The ARR bridge decomposes every dollar gained and "
                        "lost; cohort retention curves show whether the base "
                        "compounds or leaks; the magic number prices the "
                        "growth engine itself.",
            "sources": [
                "Synthetic CRM, billing, and support data (seeded, reproducible)",
                "Curated warehouse: gold.arr_bridge_monthly, "
                "gold.retention_cohorts, gold.unit_economics_monthly",
            ],
        },
        {
            "ARR": {
                "what": "Annual recurring revenue at month end \u2014 the "
                        "annualized value of every live subscription.",
                "why": "It is the number a SaaS business is valued on; "
                       "everything else on this page explains its movement.",
                "interpret": "The level matters less than the composition "
                             "behind it \u2014 read it with the bridge below. "
                             "Growth carried by 'New' is expensive; growth "
                             "carried by 'Expansion' is cheap.",
                "action": "Watch the red bars in the bridge: contraction and "
                          "churn are the leak to plug before pouring more in.",
                "source": "gold.arr_bridge_monthly",
            },
            "YoY growth": {
                "what": "Ending ARR versus the same month one year earlier.",
                "why": "Year-over-year strips out seasonality, which monthly "
                       "comparisons can't do.",
                "interpret": "Only meaningful next to efficiency: 39% growth "
                             "at a 3.8x magic number is earned; the same "
                             "growth at 0.4x would be bought.",
                "source": "gold.arr_bridge_monthly",
            },
            "Mature-cohort NRR": {
                "what": "Net revenue retention for customer cohorts 6\u201318 "
                        "months old: starting revenue plus expansion, minus "
                        "contraction and churn.",
                "why": "NRR below 100% means the installed base shrinks every "
                       "month before a single new logo is sold \u2014 the "
                       "quietest way a SaaS company stalls.",
                "interpret": "100%+ is the healthy-SaaS line. At 89% the base "
                             "loses roughly a tenth of its revenue a year; "
                             "compare against GRR to see whether expansion is "
                             "the missing piece.",
                "action": "Build an upsell motion for the contracting segment; "
                          "the GRR/NRR gap says expansion isn't covering the leak.",
                "source": "gold.retention_cohorts",
            },
            "Live customers": {
                "what": "Accounts with positive ARR right now.",
                "why": "Revenue per account trend reveals concentration risk "
                       "\u2014 rising ARR on a flat customer count means bigger, "
                       "fewer customers.",
                "interpret": "Pair with ARR: if ARR/customer climbs steadily, "
                             "a single churned logo starts to matter a lot.",
                "source": "marts.fct_arr_monthly",
            },
        },
    )

    # ---- executive brief ---------------------------------------------------
    last12 = bridge.tail(12)
    churn_worst = bridge.nlargest(1, "churned_arr").iloc[0]
    churn_typ = bridge["churned_arr"].median()
    magic = ue.tail(12)["magic_number_proxy"].mean()
    theme.brief(
        [
            ("Growth is efficient",
             f"Trailing-12m GTM magic number of {magic:.1f}x — every $1 of S&M "
             "spend comes back as new ARR inside a year. The engine works."),
            ("Retention is the leak",
             f"NRR holds at {avg_nrr:.1%} and GRR at {mature['grr'].mean():.1%} — "
             "below the 100% line, so the installed base shrinks without new "
             "logos. Expansion isn't covering contraction + churn."),
            ("Watch the December churn spike",
             f"{churn_worst['month']:%m-%d-%Y} lost ${churn_worst['churned_arr'] / 1e3:,.0f}K "
             f"ARR vs a ${churn_typ / 1e3:,.0f}K typical month — worth a "
             "win/loss review before it repeats."),
        ],
        ACCENT,
    )

    # ---- recommended actions ----------------------------------------------
    theme.actions(
        [
            ("Autopsy the December churn spike",
             f"{churn_worst['month']:%b %Y} lost ${churn_worst['churned_arr'] / 1e3:,.0f}K "
             f"ARR — roughly {churn_worst['churned_arr'] / churn_typ:.0f}× a "
             "typical month. Run a win/loss review on those accounts before "
             "the next renewal season."),
            ("Close the expansion gap",
             f"NRR is {avg_nrr:.1%}: below 100%, the base shrinks without new "
             "logos. Package an upsell motion for the contracting segment — "
             "the GRR/NRR gap shows expansion isn't covering the leak."),
            ("Scale spend only while it holds",
             f"At a {magic:.1f}x magic number, GTM spend is earning its keep. "
             "Set a guardrail — keep increasing budget only while the ratio "
             "stays above 0.75x, the SaaS healthy line."),
        ],
        ACCENT,
    )

    # ---- ARR bridge waterfall ---------------------------------------------
    fig = go.Figure(go.Waterfall(
        measure=["absolute", "relative", "relative", "relative", "relative", "total"],
        x=["Beginning ARR", "New", "Expansion", "Contraction", "Churn", "Ending ARR"],
        y=[last12["arr_begin"].iloc[0], last12["new_arr"].sum(),
           last12["expansion_arr"].sum(), -last12["contraction_arr"].sum(),
           -last12["churned_arr"].sum(), last12["arr_end"].iloc[-1]],
        increasing=dict(marker_color=ACCENT),
        decreasing=dict(marker_color="#dc2626"),
        totals=dict(marker_color="#1e2a52"),
        connector=dict(line=dict(color="#cbd5e1", width=1.5)),
    ))
    fig.update_layout(title="ARR bridge — trailing 12 months")
    st.plotly_chart(theme.style_fig(fig, ACCENT, height=400, money="y"),
                    width="stretch", config=theme.PLOTLY_CONFIG)
    theme.note(
        "How the recurring-revenue base moved over the past year: start with "
        "beginning ARR, add new logos and expansion from existing customers, "
        "subtract downgrades (contraction) and lost accounts (churn) to reach "
        "ending ARR. The two red bars are the leak the business has to plug.")

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            theme.style_fig(
                px.line(cohorts, x="months_since_start", y=["nrr", "grr"],
                        title="Net vs gross revenue retention (cohort average)",
                        labels={"value": "Retention",
                                "months_since_start": "Months since cohort start"}),
                ACCENT, percent="y"),
            width="stretch", config=theme.PLOTLY_CONFIG,
        )
        theme.note(
            "Each line is the average customer cohort as it ages. NRR counts "
            "expansion, contraction and churn; GRR excludes expansion — the "
            "gap between them is how much upsell covers the leak. At 100% a "
            "cohort kept every dollar it started with; the steady slide below "
            "it is the compounding cost of churn.")
    with right:
        magic = px.bar(ue, x="month", y="magic_number_proxy",
                       title="GTM efficiency (new ARR / S&M spend, monthly)",
                       color_discrete_sequence=[ACCENT],
                       labels={"magic_number_proxy": "Magic number"})
        magic.update_traces(
            hovertemplate="%{x|%b %Y}<br>%{y:.1f}x new ARR per S&M "
                          "dollar<extra></extra>")
        st.plotly_chart(theme.style_fig(magic, ACCENT),
                        width="stretch", config=theme.PLOTLY_CONFIG)
        theme.note(
            "The magic number is new ARR added in the month divided by the "
            "sales-and-marketing spend that produced it — how many dollars of "
            "recurring revenue one S&M dollar buys. Above 1.0 pays for itself "
            "within a year; SaaS benchmarks call 0.75+ healthy. The huge first "
            "bar is a launch-month artifact: near-zero S&M spend makes the "
            "ratio explode, so read the steady-state bars, not month one.")


if __name__ == "__main__":
    main()
