import os
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="CRM Sales Dashboard", page_icon="📊", layout="wide")

# ----------------------------------------------------------------------------
# Finance palette
# ----------------------------------------------------------------------------
NAVY = "#0B2E63"
BLUE = "#1D4ED8"
GREEN = "#047857"
RED = "#B91C1C"
TEAL = "#0E7490"
VIOLET = "#6D28D9"
SLATE = "#94A3B8"
AMBER = "#B45309"
INK = "#0F172A"
LABEL = "#334155"
MUTED = "#64748B"
GRID = "#E5E8EC"
FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'

STAGE_ORDER = ["Prospecting", "Engaging", "Won", "Lost"]
OPEN_STAGES = ["Prospecting", "Engaging"]
STAGE_COLORS = {"Prospecting": SLATE, "Engaging": AMBER, "Won": GREEN, "Lost": RED}
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}

# ----------------------------------------------------------------------------
# Styling (plain CSS — hardcoded colors to avoid f-string brace issues)
# ----------------------------------------------------------------------------
st.markdown("""<style>
.stApp { background:#F4F6F8; }
.block-container { padding-top:2rem; padding-bottom:3rem; max-width:1320px; }
html, body, [class*="css"] { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
#MainMenu, footer { visibility:hidden; }
header[data-testid="stHeader"] { display:none; }
[data-testid="stExpander"] { border:1px solid #DDE1E6; border-radius:10px; background:#FFFFFF; }
[data-testid="stExpander"] summary p { color:#0B2E63 !important; font-weight:600; font-size:.92rem; }
[data-testid="stExpander"] p, [data-testid="stExpander"] li { color:#1F2937; }
[data-testid="stCaptionContainer"] p { color:#5A6572 !important; }
span[data-baseweb="tag"] { background-color:#0B2E63 !important; color:#FFFFFF !important; }
span[data-baseweb="tag"] span { color:#FFFFFF !important; }
.fin-desc { font-size:.95rem; color:#334155; line-height:1.55; max-width:1120px; margin:.15rem 0 .7rem; }

.fin-title { font-size:1.85rem; font-weight:700; color:#0B2E63; letter-spacing:-.01em; }
.fin-meta { font-size:.9rem; color:#64748B; margin-top:.12rem; font-weight:500; }
.fin-rule { border:none; border-top:2px solid #0B2E63; margin:.55rem 0 .4rem; }
.section-h { font-size:.82rem; font-weight:700; color:#0B2E63; text-transform:uppercase;
  letter-spacing:.05em; margin:1.5rem 0 .55rem; }

[data-testid="stMetric"] {
  background:#FFFFFF; border:1px solid #DDE1E6; border-radius:10px;
  padding:15px 18px 13px; position:relative; overflow:hidden;
  box-shadow:0 1px 2px rgba(16,24,40,.05);
}
[data-testid="stMetric"]::before {
  content:""; position:absolute; top:0; left:0; right:0; height:3px; background:#0B2E63;
}
[data-testid="stMetricLabel"] p {
  font-size:.72rem; letter-spacing:.06em; text-transform:uppercase;
  color:#5A6572; font-weight:600;
}
[data-testid="stMetricValue"] {
  font-size:1.68rem; color:#0F172A; font-weight:700;
  font-feature-settings:"tnum" 1,"lnum" 1;
}

[data-testid="stSidebar"] { background:#FFFFFF; border-right:1px solid #DDE1E6; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 { font-size:1rem; color:#0B2E63;
  text-transform:uppercase; letter-spacing:.04em; }
[data-testid="stSidebar"] label { color:#334155; font-weight:600; }

.fin-table { width:100%; border-collapse:collapse; font-size:.86rem;
  font-feature-settings:"tnum" 1,"lnum" 1; }
.fin-table th { text-align:left; color:#5A6572; font-weight:600; font-size:.7rem;
  text-transform:uppercase; letter-spacing:.04em; padding:9px 12px; border-bottom:2px solid #DDE1E6; }
.fin-table th.num, .fin-table td.num { text-align:right; }
.fin-table td { padding:8px 12px; border-bottom:1px solid #EEF1F4; color:#0F172A; }
.fin-table tbody tr:last-child td { border-bottom:none; }
.fin-table tr:hover td { background:#F7F9FB; }
.fin-pos { color:#047857; font-weight:600; }
</style>""", unsafe_allow_html=True)


def sh(text):
    st.markdown(f'<div class="section-h">{text}</div>', unsafe_allow_html=True)


def html_table(df, right_cols=()):
    head = "".join(
        f'<th class="{"num" if c in right_cols else ""}">{c}</th>' for c in df.columns)
    body = ""
    for _, r in df.iterrows():
        body += "<tr>" + "".join(
            f'<td class="{"num" if c in right_cols else ""}">{r[c]}</td>'
            for c in df.columns) + "</tr>"
    st.markdown(
        f'<table class="fin-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>',
        unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------
def _find(name):
    for cand in (os.path.join("assets", name), name, os.path.join("data", name)):
        if os.path.exists(cand):
            return cand
    return os.path.join("assets", name)


@st.cache_data
def load_data():
    pipe = pd.read_csv(_find("sales_pipeline.csv"))
    prod = pd.read_csv(_find("products.csv"))
    acc = pd.read_csv(_find("accounts.csv"))
    team = pd.read_csv(_find("sales_teams.csv"))

    key = prod["product"].str.replace(" ", "", regex=False).str.lower()
    canon = dict(zip(key, prod["product"]))
    pipe["product"] = (
        pipe["product"].str.replace(" ", "", regex=False).str.lower().map(canon)
        .fillna(pipe["product"]))

    pipe = pipe.merge(prod, on="product", how="left")
    pipe = pipe.merge(acc[["account", "sector"]], on="account", how="left")
    pipe = pipe.merge(team, on="sales_agent", how="left")

    pipe["close_date"] = pd.to_datetime(pipe["close_date"], errors="coerce")
    pipe["close_quarter"] = pipe["close_date"].dt.to_period("Q").astype(str)
    pipe["close_month"] = pipe["close_date"].dt.to_period("M").astype(str)
    pipe.loc[pipe["close_quarter"] == "NaT", "close_quarter"] = None
    pipe.loc[pipe["close_month"] == "NaT", "close_month"] = None
    return pipe


def money(v):
    v = float(v or 0)
    if abs(v) >= 1e6:
        return f"${v / 1e6:,.2f}M"
    if abs(v) >= 1e4:
        return f"${v / 1e3:,.0f}K"
    return f"${v:,.0f}"


def style(fig, height=320, legend=False, currency=None):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=16, t=34 if legend else 10, b=8),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family=FONT, size=13, color=LABEL),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                    title_text="", font=dict(size=12, color=LABEL)),
        colorway=[BLUE],
        hoverlabel=dict(font_family=FONT, font_size=13),
    )
    fig.update_xaxes(title_text="", showgrid=False, zeroline=False,
                     linecolor=GRID, tickcolor=GRID, tickfont=dict(color=LABEL, size=12))
    fig.update_yaxes(title_text="", gridcolor=GRID, zeroline=False,
                     linecolor=GRID, tickcolor=GRID, tickfont=dict(color=LABEL, size=12))
    if currency == "x":
        fig.update_xaxes(tickprefix="$", tickformat=".2s")
    if currency == "y":
        fig.update_yaxes(tickprefix="$", tickformat=".2s")
    return fig


def hbar(df, xcol, ycol, color=BLUE, height=300):
    fig = px.bar(df, x=xcol, y=ycol, orientation="h")
    fig.update_traces(marker_color=color, texttemplate="$%{x:.3s}",
                      textposition="outside", cliponaxis=False,
                      textfont=dict(color=INK, size=12),
                      hovertemplate="%{y}<br>$%{x:,.0f}<extra></extra>")
    fig = style(fig, height=height, currency="x")
    m = df[xcol].max() if len(df) else 1
    fig.update_xaxes(range=[0, m * 1.2])
    return fig


pipe = load_data()

# ----------------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------------
st.sidebar.header("Filters")
regions = sorted(pipe["regional_office"].dropna().unique())
series = sorted(pipe["series"].dropna().unique())
quarters = sorted([q for q in pipe["close_quarter"].dropna().unique()])

sel_region = st.sidebar.multiselect(
    "Regional office", regions, default=regions,
    help="Limit every metric to specific sales regions (Central, East, West).")
sel_series = st.sidebar.multiselect(
    "Product series", series, default=series,
    help="Focus on one or more product lines (GTX, MG, GTK).")
sel_quarter = st.sidebar.multiselect(
    "Close quarter", quarters, default=quarters,
    help="Restrict closed-deal metrics (revenue, win rate, won vs lost) to these 2017 quarters.")
top_n = st.sidebar.slider(
    "Top agents shown", 5, 30, 10,
    help="How many sales reps to display in the leaderboard chart.")
st.sidebar.divider()
st.sidebar.caption(
    "Revenue and win rate reflect closed deals in the selected quarters. "
    "Open pipeline is a live snapshot and ignores the quarter filter, "
    "because open deals have no close date yet.")

base = pipe[pipe["regional_office"].isin(sel_region) & pipe["series"].isin(sel_series)]
closed = base[base["deal_stage"].isin(["Won", "Lost"])]
closed = closed[closed["close_quarter"].isin(sel_quarter)]
won = closed[closed["deal_stage"] == "Won"]
lost = closed[closed["deal_stage"] == "Lost"]
open_deals = base[base["deal_stage"].isin(OPEN_STAGES)]

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
cd = pipe["close_date"].dropna()
period = f"{cd.min():%b %Y} \u2013 {cd.max():%b %Y}" if len(cd) else "2017"
st.markdown('<div class="fin-title">CRM Sales Dashboard</div>', unsafe_allow_html=True)
st.markdown(f'<div class="fin-meta">Sales performance report &nbsp;&middot;&nbsp; deals closed {period}</div>',
            unsafe_allow_html=True)
st.markdown('<hr class="fin-rule"/>', unsafe_allow_html=True)
st.markdown(
    '<div class="fin-desc">This report turns raw sales-opportunity records into a performance '
    'view of the 2017 pipeline — revenue booked from won deals, how often deals convert, and which '
    'products, regions, sectors, and reps drive the numbers, alongside what is still open. '
    'Use the sidebar filters to slice every metric by region, product line, or quarter.</div>',
    unsafe_allow_html=True)

with st.expander("Definitions & how to read the numbers"):
    st.markdown("""
**Filters (left sidebar)**
- **Regional office** — narrow every chart to one or more sales regions.
- **Product series** — focus on specific product lines.
- **Close quarter** — restrict closed-deal metrics (revenue, win rate, won vs lost) to chosen quarters.
- **Top agents shown** — set how many reps appear in the agent leaderboard.

**How to read the numbers**
- **Revenue** and **average deal size** count *won* deals only; lost deals book zero.
- **Win rate** = won divided by (won + lost) among closed deals.
- **Open pipeline** is a live snapshot of Engaging and Prospecting deals; its value is estimated
  from product list price, and it deliberately ignores the quarter filter.
- Q1 shows an unusually high win rate because deals only begin closing in March 2017 — treat it as a partial quarter.
""")

st.write("")

# ----------------------------------------------------------------------------
# KPI row
# ----------------------------------------------------------------------------
revenue = won["close_value"].sum()
n_won, n_lost = len(won), len(lost)
win_rate = n_won / (n_won + n_lost) if (n_won + n_lost) else 0
avg_deal = revenue / n_won if n_won else 0
open_val = open_deals["sales_price"].sum()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Revenue (won)", money(revenue))
c2.metric("Win rate", f"{win_rate:.1%}")
c3.metric("Deals won", f"{n_won:,}")
c4.metric("Avg deal size", money(avg_deal))
c5.metric("Open pipeline", f"{len(open_deals):,}", help=f"Estimated {money(open_val)} at list price")

# ----------------------------------------------------------------------------
# Revenue over time
# ----------------------------------------------------------------------------
sh("Revenue over time")
if won.empty:
    st.info("No won deals match the current filters.")
else:
    monthly = won.groupby("close_month", as_index=False)["close_value"].sum()
    fig = px.area(monthly, x="close_month", y="close_value", markers=True)
    fig.update_traces(line_color=BLUE, line_width=2.5, fillcolor="rgba(29,78,216,0.09)",
                      marker=dict(size=6, color=BLUE),
                      hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>")
    st.plotly_chart(style(fig, 300, currency="y"), use_container_width=True, config=PLOT_CONFIG)

# ----------------------------------------------------------------------------
# Revenue by series + region
# ----------------------------------------------------------------------------
a, b = st.columns(2)
with a:
    sh("Revenue by product series")
    if not won.empty:
        d = won.groupby("series", as_index=False)["close_value"].sum().sort_values("close_value")
        st.plotly_chart(hbar(d, "close_value", "series"), use_container_width=True, config=PLOT_CONFIG)
with b:
    sh("Revenue by region")
    if not won.empty:
        d = won.groupby("regional_office", as_index=False)["close_value"].sum().sort_values("close_value")
        st.plotly_chart(hbar(d, "close_value", "regional_office", color=TEAL),
                        use_container_width=True, config=PLOT_CONFIG)

# ----------------------------------------------------------------------------
# Revenue by sector + top agents
# ----------------------------------------------------------------------------
a, b = st.columns(2)
with a:
    sh("Revenue by client sector")
    sec = won.dropna(subset=["sector"])
    if not sec.empty:
        d = sec.groupby("sector", as_index=False)["close_value"].sum().sort_values("close_value")
        st.plotly_chart(hbar(d, "close_value", "sector", color=VIOLET, height=390),
                        use_container_width=True, config=PLOT_CONFIG)
with b:
    sh(f"Top {top_n} agents by revenue")
    if not won.empty:
        d = (won.groupby("sales_agent", as_index=False)["close_value"].sum()
             .sort_values("close_value", ascending=False).head(top_n).sort_values("close_value"))
        st.plotly_chart(hbar(d, "close_value", "sales_agent", color=NAVY, height=390),
                        use_container_width=True, config=PLOT_CONFIG)

# ----------------------------------------------------------------------------
# Won vs lost by quarter + stage mix
# ----------------------------------------------------------------------------
a, b = st.columns(2)
with a:
    sh("Won vs lost by quarter")
    if not closed.empty:
        q = closed.groupby(["close_quarter", "deal_stage"], as_index=False).size()
        fig = px.bar(q, x="close_quarter", y="size", color="deal_stage", barmode="group",
                     color_discrete_map={"Won": GREEN, "Lost": RED})
        fig.update_traces(texttemplate="%{y}", textposition="outside",
                          textfont=dict(color=INK, size=11),
                          hovertemplate="%{x}<br>%{y} deals<extra></extra>")
        st.plotly_chart(style(fig, 340, legend=True), use_container_width=True, config=PLOT_CONFIG)
with b:
    sh("Pipeline stage mix")
    if not base.empty:
        m = base.groupby("deal_stage", as_index=False).size()
        m["deal_stage"] = pd.Categorical(m["deal_stage"], STAGE_ORDER, ordered=True)
        m = m.sort_values("deal_stage")
        fig = px.bar(m, x="deal_stage", y="size", color="deal_stage", text_auto=True,
                     color_discrete_map=STAGE_COLORS)
        fig.update_traces(textposition="outside", textfont=dict(color=INK, size=11),
                          hovertemplate="%{x}<br>%{y} deals<extra></extra>")
        fig.update_layout(showlegend=False)
        st.plotly_chart(style(fig, 340), use_container_width=True, config=PLOT_CONFIG)

st.markdown('<hr class="fin-rule" style="margin-top:1.6rem;border-top:1px solid #DDE1E6;"/>',
            unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Detail tables (HTML — avoids the Arrow serialization crash on rerun)
# ----------------------------------------------------------------------------
with st.expander("Agent leaderboard"):
    if not closed.empty:
        lb = closed.assign(is_won=(closed["deal_stage"] == "Won")).groupby("sales_agent").agg(
            revenue=("close_value", "sum"), won=("is_won", "sum"), deals=("deal_stage", "size"))
        lb = lb.sort_values("revenue", ascending=False).reset_index()
        lb["win_rate"] = (lb["won"] / lb["deals"] * 100).round(0).astype(int).astype(str) + "%"
        lb["revenue"] = lb["revenue"].map(money)
        lb.columns = ["Sales agent", "Revenue", "Won", "Deals", "Win rate"]
        html_table(lb, right_cols=["Revenue", "Won", "Deals", "Win rate"])

with st.expander("Largest won deals (top 100)"):
    top = won.sort_values("close_value", ascending=False).head(100).copy()
    top["close_date"] = top["close_date"].dt.strftime("%Y-%m-%d")
    top["close_value"] = top["close_value"].map(lambda x: f"${x:,.0f}")
    show = top[["close_date", "sales_agent", "product", "account", "sector",
                "regional_office", "close_value"]].rename(columns={
        "close_date": "Close date", "sales_agent": "Agent", "product": "Product",
        "account": "Account", "sector": "Sector", "regional_office": "Region",
        "close_value": "Value"})
    html_table(show, right_cols=["Value"])