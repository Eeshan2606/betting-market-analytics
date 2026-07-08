"""Market intelligence dashboard over the gold and silver layers.

Read-only DuckDB connection: never contends with the pipeline's write lock.
"""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "warehouse.duckdb"

st.set_page_config(
    page_title="Betting Market Intelligence",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return con.sql(sql).df()


# ---------- data ----------

divergence = query("""
    select * from gold.mart_world_cup_divergence
    order by snapshot_date, team
""")

poly_history = query("""
    select snapshot_ts, world_cup_team as team, yes_price
    from silver.stg_polymarket_markets
    where world_cup_team is not null
    order by snapshot_ts
""")

bookmaker_latest = query("""
    with latest as (
        select max(snapshot_ts) as ts
        from silver.stg_bookmaker_odds
        where sport_key = 'soccer_fifa_world_cup_winner'
    )
    select o.bookmaker, o.outcome_name as team, o.implied_probability
    from silver.stg_bookmaker_odds o
    join latest l on o.snapshot_ts = l.ts
    where o.sport_key = 'soccer_fifa_world_cup_winner'
      and o.market_type = 'outrights'
""")

health = query("""
    select 'polymarket_markets' as source,
           count(*) as rows,
           max(snapshot_ts) as latest_snapshot
    from bronze.polymarket_markets
    union all
    select 'bookmaker_odds',
           count(*),
           max(snapshot_ts)
    from bronze.bookmaker_odds
""")

latest_date = divergence["snapshot_date"].max()
latest = divergence[divergence["snapshot_date"] == latest_date]

# ---------- header ----------

st.title("Betting Market Intelligence")
st.caption(
    "DraftKings vs Polymarket — FIFA World Cup 2026 winner market. "
    "Bookmaker probabilities are vig-normalized for fair comparison. "
    "Snapshots collected twice daily by an automated pipeline."
)

k1, k2, k3, k4 = st.columns(4)
top_div = latest.loc[latest["abs_divergence"].idxmax()]
k1.metric("Latest snapshot", str(latest_date))
k2.metric("Teams tracked", f"{latest['team'].nunique()}")
k3.metric(
    "Largest divergence",
    f"{top_div['abs_divergence'] * 100:.1f} pts",
    help=f"{top_div['team']}: bookmaker vs prediction market",
)
k4.metric(
    "Avg bookmaker margin (vig share)",
    f"{latest['vig_share'].mean() * 100:.1f} pts",
    help="Mean probability inflation removed during normalization",
)

st.divider()

# ---------- section 1: the market right now ----------

st.subheader("The market right now")
c1, c2 = st.columns([3, 2])

melted = latest.melt(
    id_vars="team",
    value_vars=["draftkings_prob", "polymarket_prob"],
    var_name="source",
    value_name="probability",
)
melted["source"] = melted["source"].map(
    {"draftkings_prob": "DraftKings (vig-normalized)", "polymarket_prob": "Polymarket"}
)
fig = px.bar(
    melted.sort_values("probability", ascending=False),
    x="team",
    y="probability",
    color="source",
    barmode="group",
    labels={"probability": "Implied probability", "team": ""},
)
fig.update_layout(yaxis_tickformat=".0%", legend_title="")
c1.plotly_chart(fig, use_container_width=True)

table = latest.sort_values("abs_divergence", ascending=False)[
    ["team", "draftkings_prob", "polymarket_prob", "divergence"]
]
c2.dataframe(
    table.style.format(
        {
            "draftkings_prob": "{:.1%}",
            "polymarket_prob": "{:.1%}",
            "divergence": "{:+.2%}",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# ---------- section 2: movement over time ----------

st.subheader("Price movement")
teams = sorted(poly_history["team"].dropna().unique())
default_teams = list(
    latest.sort_values("polymarket_prob", ascending=False)["team"].head(4)
)
selected = st.multiselect("Teams", teams, default=default_teams)

if selected:
    hist = poly_history[poly_history["team"].isin(selected)]
    fig2 = px.line(
        hist,
        x="snapshot_ts",
        y="yes_price",
        color="team",
        markers=True,
        labels={"yes_price": "Polymarket implied probability", "snapshot_ts": ""},
    )
    fig2.update_layout(yaxis_tickformat=".0%", legend_title="")
    st.plotly_chart(fig2, use_container_width=True)
    st.caption(
        "Polymarket snapshots (higher frequency than the daily divergence grain). "
        "History deepens with every pipeline run."
    )

# ---------- section 3: across bookmakers ----------

st.subheader("Across bookmakers")
if not bookmaker_latest.empty:
    pivot_teams = list(
        latest.sort_values("polymarket_prob", ascending=False)["team"].head(6)
    )
    bm = bookmaker_latest[bookmaker_latest["team"].isin(pivot_teams)]
    fig3 = px.bar(
        bm,
        x="team",
        y="implied_probability",
        color="bookmaker",
        barmode="group",
        labels={"implied_probability": "Raw implied probability", "team": ""},
    )
    fig3.update_layout(yaxis_tickformat=".0%", legend_title="")
    st.plotly_chart(fig3, use_container_width=True)
    st.caption(
        "Raw (pre-normalization) probabilities — differences between books "
        "reflect both opinion and margin."
    )

# ---------- section 4: pipeline health ----------

st.divider()
st.subheader("Pipeline health")
h1, h2 = st.columns(2)
for col, (_, row) in zip((h1, h2), health.iterrows()):
    col.metric(
        f"bronze.{row['source']}",
        f"{int(row['rows']):,} rows",
        help=f"Latest snapshot: {row['latest_snapshot']}",
    )
st.caption(
    "Bronze layer row counts. Data refreshes on the 08:00 / 20:00 scheduled runs."
)