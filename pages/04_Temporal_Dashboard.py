import streamlit as st
import altair as alt
import pandas as pd
from lib.narratives_utils import load_data, time_series_frames

st.set_page_config(page_title="Temporal Dashboard", layout="wide")

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

st.title("Temporal Dashboard")

df = load_data()
if not df["date_dt"].notna().any():
    st.error("No valid dates in dataset.")
    st.stop()

dates = df["date_dt"].dropna()
min_dt = dates.min().date()
max_dt = dates.max().date()

st.sidebar.header("Temporal Settings")
freq = st.sidebar.selectbox("Granularity", ["Weekly", "Monthly", "Yearly"], index=0)
freq_code_map = {
    "Weekly": "W",
    "Monthly": "M",
    "Yearly": "Y"
}
freq_code = freq_code_map[freq]

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

ts = time_series_frames(df_range, freq=freq_code)
if ts.empty:
    st.info("No data in selected range.")
    st.stop()

# Top frames overall (to filter selection)
overall = (
    ts.groupby("narrative frame")["articles"]
      .sum().sort_values(ascending=False).head(30).index.tolist()
)

selected_frames = st.multiselect(
    "Select frames (empty = top 8 auto)",
    options=overall,
    default=overall[:8]
)

if not selected_frames:
    selected_frames = overall[:8]

plot_df = ts[ts["narrative frame"].isin(selected_frames)].copy()

line = alt.Chart(plot_df).mark_line(point=True).encode(
    x=alt.X("period:T", title="Period"),
    y=alt.Y("prevalence:Q", axis=alt.Axis(format=".0%"), title="Prevalence"),
    color=alt.Color("narrative frame:N", title="Frame"),
    tooltip=[
        "narrative frame",
        alt.Tooltip("period:T", title="Period"),
        alt.Tooltip("articles:Q", title="# Articles"),
        alt.Tooltip("prevalence:Q", format=".1%", title="Prevalence")
    ]
).properties(title=f"Frame Prevalence Over Time ({freq})")

st.altair_chart(line, use_container_width=True)

# Stacked area (share of selected frames)
area = alt.Chart(plot_df).mark_area(interpolate="monotone").encode(
    x=alt.X("period:T", title="Period"),
    y=alt.Y("prevalence:Q", stack="normalize", axis=alt.Axis(format=".0%"), title="Share (selected frames)"),
    color=alt.Color("narrative frame:N", title="Frame"),
    tooltip=[
        "narrative frame",
        alt.Tooltip("period:T"),
        alt.Tooltip("prevalence:Q", format=".1%")
    ]
).properties(title="Relative Share (Selected Frames)")
st.altair_chart(area, use_container_width=True)

with st.expander("Underlying Time Series Data"):
    st.dataframe(plot_df.sort_values(["period", "narrative frame"]))