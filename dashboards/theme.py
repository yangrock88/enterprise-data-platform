"""Shared dashboard visual system.

One design language across every project: Inter/system font stack, soft
slate canvas with radial accent washes, glass cards, a navy hero band with
headline KPIs, an executive-brief strip, and a flat Plotly template (light
grid, no borders, accent-led colorway). Each app passes its own accent
color; everything else is inherited.

Labels are natural language by default: style_fig rewrites axis titles,
legend titles and legend entries from column names ("tip_rate" becomes
"Tip rate", "nrr" becomes "NRR"). Dollar hovers show one decimal.
"""

from __future__ import annotations

import streamlit as st

FONT = "Inter, Segoe UI, system-ui, sans-serif"
SLATE_900 = "#0f172a"
SLATE_600 = "#475569"
SLATE_500 = "#64748b"
BORDER = "#e2e8f0"
GRID = "rgba(15,23,42,.06)"

ACRONYMS = {
    "nrr": "NRR", "grr": "GRR", "arr": "ARR", "roi": "ROI", "cac": "CAC",
    "did": "DiD", "err": "ERR", "pmpm": "PMPM", "npi": "NPI", "kpi": "KPI",
    "sql": "SQL", "gtm": "GTM", "pct": "%", "cms": "CMS",
}
SMALL_WORDS = {"per", "of", "by", "vs", "a", "an", "the", "to", "in", "on", "at"}


def humanize(name: str) -> str:
    """'excess_readmission_ratio' -> 'Excess readmission ratio'; 'nrr' -> 'NRR'."""
    words = str(name).replace("_", " ").split()
    out = []
    for i, w in enumerate(words):
        low = w.lower()
        if low in ACRONYMS:
            out.append(ACRONYMS[low])
        elif i > 0 and low in SMALL_WORDS:
            out.append(low)
        else:
            out.append(low.capitalize())
    return " ".join(out)


def apply(accent: str) -> None:
    """Inject the CSS layer. Call once, right after st.set_page_config."""
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{ font-family: {FONT}; }}
        .stApp {{
            background:
                radial-gradient(1200px 600px at 10% -10%, {accent}1a, transparent 60%),
                radial-gradient(900px 500px at 110% 10%, rgba(30,42,82,.10), transparent 60%),
                #f8fafc;
        }}
        [data-testid="stMetric"] {{
            background: rgba(255,255,255,.85);
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 14px 18px;
            box-shadow: 0 1px 2px rgba(15,23,42,.05);
        }}
        [data-testid="stMetric"] label {{ color: {SLATE_500} !important;
            text-transform: uppercase; letter-spacing: .06em; font-size: .72rem !important; }}
        [data-testid="stMetric"] [data-testid="stMetricValue"] {{
            color: {SLATE_900}; font-weight: 800; }}
        h1, h2, h3 {{ color: {SLATE_900}; font-weight: 700; letter-spacing: -0.01em; }}
        [data-testid="stSidebar"] {{ background: #ffffff; border-right: 1px solid {BORDER}; }}
        [data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 16px;
            overflow: hidden; background: #fff; }}
        .block-container {{ padding-top: 2rem; }}
        /* Charts are read-only: never show the crosshair/zoom cursor. */
        .js-plotly-plot .nsewdrag, .js-plotly-plot .cursor-crosshair,
        .js-plotly-plot .draglayer {{
            cursor: default !important;
        }}
        /* Guide pills: the only tertiary buttons are the definition pills.
           Bordered + rounded + hover fill so they read as clickable. */
        [data-testid="stButton"] button[kind="tertiary"] {{
            border: 1.5px solid {accent};
            border-radius: 999px;
            background: #ffffff;
            color: {accent};
            font-weight: 700;
            padding: .3rem 1.05rem;
            box-shadow: 0 1px 2px rgba(15,23,42,.08);
            transition: all .15s ease-in-out;
        }}
        [data-testid="stButton"] button[kind="tertiary"]:hover {{
            background: {accent};
            color: #ffffff;
            border-color: {accent};
        }}
        [data-testid="stButton"] button[kind="tertiary"]:focus:not(:active) {{
            color: {accent};
            border-color: {accent};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, kpis: list[tuple], accent: str) -> None:
    """Navy hero band with headline KPIs (title + metrics only, no jargon
    subtitle line).

    Each KPI is (label, value) or (label, value, tooltip) — the tooltip
    shows on hover over the cell.
    """
    cells = ""
    for item in kpis:
        label, value = item[0], item[1]
        tip = f' title="{item[2]}"' if len(item) > 2 else ""
        cells += (
            f'<div style="flex:1;min-width:170px;text-align:center"{tip}>'
            f'<div style="color:rgba(255,255,255,.6);font-size:.78rem;text-transform:uppercase;'
            f'letter-spacing:.09em;margin-bottom:8px">{label}</div>'
            f'<div style="font-size:2.5rem;font-weight:800;color:#fff;line-height:1.1">{value}</div>'
            f'<div style="width:38px;height:3px;background:{accent};border-radius:2px;'
            f'margin:10px auto 0"></div>'
            f"</div>"
        )
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#1e2a52 0%,#0e1730 100%);
                    border-radius:24px;padding:30px 34px;margin-bottom:22px;
                    box-shadow:0 8px 24px rgba(14,23,48,.18)">
          <div style="font-size:1.45rem;font-weight:800;color:#fff;letter-spacing:-0.01em;
                      margin-bottom:20px">{title}</div>
          <div style="display:flex;gap:24px;flex-wrap:wrap;justify-content:space-between">{cells}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def brief(items: list[tuple[str, str]], accent: str) -> None:
    """Executive-brief strip: a row of insight cards with accent left bars."""
    cards = "".join(
        f'<div style="flex:1;min-width:240px;background:rgba(255,255,255,.85);'
        f'border:1px solid {BORDER};border-left:4px solid {accent};border-radius:14px;'
        f'padding:14px 16px;box-shadow:0 1px 2px rgba(15,23,42,.05)">'
        f'<div style="font-weight:700;color:{SLATE_900};font-size:.9rem;margin-bottom:4px">{head}</div>'
        f'<div style="color:{SLATE_600};font-size:.82rem;line-height:1.45">{body}</div>'
        f"</div>"
        for head, body in items
    )
    st.markdown(
        f'<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:22px">{cards}</div>',
        unsafe_allow_html=True,
    )


def actions(items: list[tuple[str, str]], accent: str) -> None:
    """'What to do next' strip: numbered action cards."""
    cards = ""
    for i, (head, body) in enumerate(items, 1):
        cards += (
            f'<div style="flex:1;min-width:240px;background:rgba(255,255,255,.85);'
            f'border:1px solid {BORDER};border-radius:14px;padding:14px 16px;'
            f'box-shadow:0 1px 2px rgba(15,23,42,.05)">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'<span style="display:inline-grid;place-items:center;width:20px;height:20px;'
            f'border-radius:999px;background:{accent};color:#fff;font-size:.7rem;'
            f'font-weight:800">{i}</span>'
            f'<div style="font-weight:700;color:{SLATE_900};font-size:.9rem">{head}</div>'
            f"</div>"
            f'<div style="color:{SLATE_600};font-size:.82rem;line-height:1.45">{body}</div>'
            f"</div>"
        )
    st.markdown(
        f'<div style="font-size:.95rem;font-weight:700;color:{SLATE_900};'
        f'margin:6px 0 10px">What to do next</div>'
        f'<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:22px">'
        f"{cards}</div>",
        unsafe_allow_html=True,
    )


def _guide_dialog(entries: dict):
    """Build the click-to-open definition dialog for a set of entries."""

    @st.dialog(" ", width="large")
    def _show(entry_key: str) -> None:
        name, e = entries[entry_key]
        st.markdown(f"### {name}")
        if "problem" in e:
            st.markdown("**The problem this dashboard solves**")
            st.write(e["problem"])
            if e.get("approach"):
                st.markdown("**How it answers it**")
                st.write(e["approach"])
            if e.get("sources"):
                st.markdown("**Data sources**")
                for s in e["sources"]:
                    st.markdown(f"- {s}")
        else:
            st.markdown("**What it measures**")
            st.write(e["what"])
            st.markdown("**Why it's measured**")
            st.write(e["why"])
            st.markdown("**How to interpret it**")
            st.write(e["interpret"])
            if e.get("action"):
                st.markdown("**What to do about it**")
                st.write(e["action"])
            if e.get("source"):
                st.caption(f"Source: {e['source']}")

    return _show


def guide_bar(about: dict, metrics: dict[str, dict]) -> None:
    """One aligned row of definition pills, directly under the hero band:
    'About this dashboard' first, then one pill per hero metric. Every pill
    opens a click-to-read dialog (about: problem/approach/sources; metric:
    what/why/interpret/action/source). Pill styling lives in apply() —
    bordered, rounded, hover-filled, so they read as clickable.
    """
    entries = {"about": ("About this dashboard", about)}
    entries.update({f"m{i}": pair for i, pair in enumerate(metrics.items())})
    _show = _guide_dialog(entries)
    cols = st.columns([1.7] + [1] * (len(entries) - 1))
    for (key, (name, _)), col in zip(entries.items(), cols):
        if col.button(name, key=f"guide-{key}", type="tertiary"):
            _show(key)
    st.caption("Tap a pill for definitions, sources, and how to read each "
               "number.")


def colorway(accent: str) -> list[str]:
    return [accent, "#1e2a52", "#64748b", "#94a3b8", "#cbd5e1"]


# Hide the Plotly toolbar and scroll-zoom (read-only dashboards);
# hover tooltips are unaffected. Drag interactions are disabled per-figure
# via dragmode=False in style_fig.
PLOTLY_CONFIG = {"displayModeBar": False, "displaylogo": False,
                 "scrollZoom": False}


def note(text: str) -> None:
    """One-line 'how to read this' caption tucked under a chart."""
    st.markdown(
        f'<div style="color:{SLATE_500};font-size:.8rem;margin:-12px 0 16px 4px">'
        f"{text}</div>",
        unsafe_allow_html=True,
    )


def _humanize_titles(fig) -> None:
    for axis in (fig.layout.xaxis, fig.layout.yaxis):
        if axis.title and axis.title.text:
            axis.title.text = humanize(axis.title.text)
    if fig.layout.legend and fig.layout.legend.title and fig.layout.legend.title.text:
        fig.layout.legend.title.text = humanize(fig.layout.legend.title.text)
    if fig.layout.coloraxis and fig.layout.coloraxis.colorbar:
        cb_title = fig.layout.coloraxis.colorbar.title
        if cb_title and cb_title.text:
            cb_title.text = humanize(cb_title.text)
    for trace in fig.data:
        if getattr(trace, "name", None):
            trace.name = humanize(trace.name)


def _x_is_date(fig) -> bool:
    if not fig.data:
        return False
    x = getattr(fig.data[0], "x", None)
    return x is not None and "datetime" in str(getattr(x, "dtype", "")).lower()


def style_fig(fig, accent: str, height: int = 340,
              money: str | None = None, percent: str | None = None):
    """Apply the flat modern template. `money`/`percent` = "x" or "y" axis
    formatting. Dates render MM-DD-YYYY; dollars are whole with commas."""
    fig.update_layout(
        template=None,
        height=height,
        font=dict(family=FONT, color=SLATE_600, size=12.5),
        title=dict(font=dict(size=15, color=SLATE_900), x=0.01, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=colorway(accent),
        margin=dict(l=8, r=8, t=48, b=8),
        hoverlabel=dict(bgcolor="#ffffff", font_size=12.5, font_family=FONT,
                        bordercolor=BORDER),
        legend=dict(orientation="h", yanchor="bottom", y=1.0,
                    title=None, font=dict(size=11.5)),
        dragmode=False,  # no box-zoom / lasso / pan; hover still works
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=BORDER)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=BORDER)
    date_x = _x_is_date(fig)
    if date_x:
        fig.update_xaxes(tickformat="%m-%d-%Y")
    xhov = "%{x|%m-%d-%Y}" if date_x else "%{x}"
    if money == "y":
        fig.update_yaxes(tickformat="$,.0f")
        fig.update_traces(
            hovertemplate=xhov + "<br>$%{y:,.0f}<extra></extra>")
    elif money == "x":
        fig.update_xaxes(tickformat="$,.0f")
        fig.update_traces(hovertemplate="%{y}<br>$%{x:,.0f}<extra></extra>")
    if percent == "y":
        fig.update_yaxes(tickformat=".0%")
        fig.update_traces(
            hovertemplate=xhov + "<br>%{y:.1%}<extra></extra>")
    elif percent == "x":
        fig.update_xaxes(tickformat=".1%")
        fig.update_traces(hovertemplate="%{y}<br>%{x:.1%}<extra></extra>")
    if date_x and money is None and percent is None:
        fig.update_traces(
            hovertemplate=xhov + "<br>%{y:,.0f}<extra></extra>")
    _humanize_titles(fig)
    return fig


def geo_defaults(fig, accent_scale: list[str] | None = None,
                 midpoint: float | None = None):
    """Choropleth styling in the same language."""
    fig.update_geos(bgcolor="rgba(0,0,0,0)", lakecolor="#f1f5f9",
                    landcolor="#f1f5f9", subunitcolor="#ffffff")
    kwargs = dict(colorbar=dict(thickness=12, outlinewidth=0,
                                tickfont=dict(size=11)))
    if accent_scale is not None:
        kwargs["colorscale"] = accent_scale
    if midpoint is not None:
        kwargs["cmid"] = midpoint
    fig.update_coloraxes(**kwargs)
    return fig
