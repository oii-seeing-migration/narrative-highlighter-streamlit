import streamlit as st
import altair as alt
import pandas as pd
from lib.narratives_utils import load_data, aggregate_range

st.set_page_config(page_title="Aggregative Dashboard", layout="wide")

st.title("Aggregative Dashboard")

df = load_data()
if df["date_dt"].notna().any():
    dates = df["date_dt"].dropna()
    min_dt = dates.min().date()
    max_dt = dates.max().date()
    st.sidebar.header("Filter")
    picked = st.sidebar.date_input(
        "Date range",
        value=(min_dt, max_dt),
        min_value=min_dt,
        max_value=max_dt
    )
    if isinstance(picked, tuple) and len(picked) == 2:
        start_date, end_date = picked
    else:
        start_date = end_date = picked
    mask = (df["date_dt"].dt.date >= start_date) & (df["date_dt"].dt.date <= end_date)
    df_range = df[mask].copy()
else:
    st.info("No valid date column; using full dataset.")
    df_range = df

agg = aggregate_range(df_range)
st.write(f"Articles in range: {agg['total_articles']}")

# -------------------------------------------------
# Frames bar chart (ONLY number of articles retained)
# -------------------------------------------------
frames = agg["frames_summary"].head(25)
frames_h = max(24 * len(frames), 360)
frames_chart = alt.Chart(frames).mark_bar().encode(
    x=alt.X("articles:Q", title="# Articles"),
    y=alt.Y(
        "narrative frame:N",
        sort="-x",
        axis=alt.Axis(labelLimit=0, labelOverlap=False),
        title="Narrative Frame"
    ),
    # Single color (remove other encodings since only articles matter)
    color=alt.value("#1f77b4"),
    tooltip=[
        alt.Tooltip("narrative frame:N", title="Frame"),
        alt.Tooltip("articles:Q", title="# Articles")
    ],
).properties(title="Top Frames (by # Articles)", height=frames_h)
st.altair_chart(frames_chart, use_container_width=True)

# -------------------------------------------------
# Meso narratives: attach dominant parent frame and simplify
# Label format: Frame: Meso Narrative
# -------------------------------------------------
# Use exploded annotations to find dominant (most frequent) frame per meso
if "exploded" in agg:
    ex = agg["exploded"]
else:
    # Fallback: reconstruct minimal exploded if not returned
    ex = pd.DataFrame()

if not ex.empty:
    meso_parent = (
        ex[ex["meso narrative"].notna() & (ex["meso narrative"] != "")]
        .groupby("meso narrative")["narrative frame"]
        .agg(lambda s: s.value_counts().idxmax() if not s.value_counts().empty else "")
        .reset_index()
        .rename(columns={"narrative frame": "parent_frame"})
    )
    meso = agg["meso_summary"].merge(meso_parent, on="meso narrative", how="left")
else:
    meso = agg["meso_summary"].copy()
    meso["parent_frame"] = ""

meso = meso.head(25)
meso["frame_meso_label"] = meso.apply(
    lambda r: f"[{r['parent_frame']}]: {r['meso narrative']}" if r["parent_frame"] else r["meso narrative"],
    axis=1
)

meso_h = max(24 * len(meso), 360)
meso_chart = alt.Chart(meso).mark_bar().encode(
    x=alt.X("articles:Q", title="# Articles"),
    y=alt.Y(
        "frame_meso_label:N",
        sort="-x",
        axis=alt.Axis(
            labelLimit=0,
            labelOverlap=False,
            title="Frame: Meso Narrative",
            titleAngle=270,
            titlePadding=300,
            labelPadding=6
        )
    ),
    # Color bars by parent frame to visually separate groups
    color=alt.Color("parent_frame:N", title="Frame", legend=alt.Legend(columns=1)),
    tooltip=[
        alt.Tooltip("parent_frame:N", title="Frame"),
        alt.Tooltip("meso narrative:N", title="Meso Narrative"),
        alt.Tooltip("articles:Q", title="# Articles")
    ],
).properties(title="Top Meso Narratives (by # Articles)", height=meso_h)
st.altair_chart(meso_chart, use_container_width=True)


with st.expander("Raw Frame Data"):
    st.dataframe(agg["frames_summary"][["narrative frame", "articles", "prevalence", "intensity"]])

with st.expander("Raw Meso Data"):
    st.dataframe(meso[["parent_frame", "meso narrative", "articles"]])