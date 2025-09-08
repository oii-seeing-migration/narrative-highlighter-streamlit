import streamlit as st
import altair as alt
import pandas as pd
from lib.narratives_utils import load_data, aggregate_range

st.set_page_config(page_title="Aggregative Dashboard", layout="wide")

# Sidebar navigation
st.sidebar.subheader("Navigation")
try:
    st.sidebar.page_link("navigation_page.py", label="Navigation Page", icon="🧭")
    st.sidebar.page_link("pages/01_Narratives_on_Articles.py", label="Narratives on Articles", icon="📰")
    st.sidebar.page_link("pages/02_Aggregative_Dashboard.py", label="Aggregative Dashboard", icon="📊")
    st.sidebar.page_link("pages/03_Contrastive_Dashboard.py", label="Contrastive Dashboard", icon="⚖️")
    st.sidebar.page_link("pages/04_Temporal_Dashboard.py", label="Temporal Dashboard", icon="⏱")
except Exception:
    pass

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

frames = agg["frames_summary"].head(25)
frames_h = max(24 * len(frames), 360)
frames_chart = alt.Chart(frames).mark_bar().encode(
    x=alt.X("articles:Q", title="# Articles"),
    y=alt.Y("narrative frame:N", sort="-x", axis=alt.Axis(labelLimit=0, labelOverlap=False), title="Narrative Frame"),
    tooltip=[
        "narrative frame",
        "articles:Q",
        "fragments:Q",
        alt.Tooltip("prevalence:Q", format=".1%"),
        alt.Tooltip("intensity:Q", format=".2f"),
    ],
    color=alt.Color("prevalence:Q", scale=alt.Scale(scheme="blues"), legend=None),
).properties(title="Top Frames (by # Articles)", height=frames_h)
st.altair_chart(frames_chart, use_container_width=True)

meso = agg["meso_summary"].head(25)
meso_h = max(24 * len(meso), 360)
meso_chart = alt.Chart(meso).mark_bar().encode(
    x=alt.X("articles:Q", title="# Articles"),
    y=alt.Y(
        "meso narrative:N",
        sort="-x",
        axis=alt.Axis(
            labelLimit=0,
            labelOverlap=False,
            title="Meso Narrative",
            titleAngle=270,      # keep vertical
            titlePadding=140,    # increase to push title further left
            labelPadding=6
        )
    ),
    tooltip=[
        "meso narrative",
        "articles:Q",
        "fragments:Q",
        alt.Tooltip("prevalence:Q", format=".1%"),
        alt.Tooltip("intensity:Q", format=".2f")
    ],
    color=alt.Color("articles:Q", legend=None, scale=alt.Scale(scheme="teals"))
).properties(title="Top Meso Narratives (by # Articles)", height=meso_h)
st.altair_chart(meso_chart, use_container_width=True)

# Intensity vs Prevalence scatter (frames)
scatter = alt.Chart(agg["frames_summary"]).mark_circle(size=160).encode(
    x=alt.X("prevalence:Q", axis=alt.Axis(format=".0%"), title="Prevalence (share of articles)"),
    y=alt.Y("intensity:Q", title="Intensity (fragments per article w/ frame)"),
    size=alt.Size("articles:Q", title="# Articles"),
    color=alt.Color("articles:Q", scale=alt.Scale(scheme="plasma"), legend=None),
    tooltip=["narrative frame", "articles", alt.Tooltip("prevalence:Q", format=".1%"), alt.Tooltip("intensity:Q", format=".2f")]
).properties(title="Frames: Prevalence vs Intensity")
st.altair_chart(scatter, use_container_width=True)

with st.expander("Raw Data"):
    st.dataframe(agg["frames_summary"])