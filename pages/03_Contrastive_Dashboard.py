import streamlit as st
import altair as alt
import pandas as pd
from lib.narratives_utils import load_data, compute_frame_contrast

st.set_page_config(page_title="Contrastive Dashboard", layout="wide")

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

st.title("Contrastive Dashboard")

df = load_data()
dates = df["date_dt"].dropna()
if dates.empty:
    st.error("No valid dates.")
    st.stop()

min_dt = dates.min().date()
max_dt = dates.max().date()
mid = min_dt + (max_dt - min_dt) / 2

st.sidebar.header("Periods")
period_a = st.sidebar.date_input("Period A", value=(min_dt, mid), min_value=min_dt, max_value=max_dt, key="pa")
period_b = st.sidebar.date_input("Period B", value=(mid, max_dt), min_value=min_dt, max_value=max_dt, key="pb")

def _norm(p):
    if isinstance(p, tuple) and len(p) == 2:
        return tuple(sorted(p))
    return (p, p)

period_a = _norm(period_a)
period_b = _norm(period_b)

min_support = st.sidebar.slider("Min combined article support", 1, 50, 3, 1)
top_n = st.sidebar.slider("Top N frames (by |salience|)", 5, 40, 20, 1)

contrast_df, agg_a, agg_b = compute_frame_contrast(df, period_a, period_b, min_articles_total=min_support)

st.caption(f"Period A: {period_a[0]} → {period_a[1]} | Period B: {period_b[0]} → {period_b[1]}")

if contrast_df.empty:
    st.info("No frames pass support threshold.")
    st.stop()

contrast_df["abs_salience"] = contrast_df["salience_score"].abs()
top_contrast = contrast_df.sort_values("abs_salience", ascending=False).head(top_n).copy()

# Salience bar
height = max(24 * len(top_contrast), 320)
bar = alt.Chart(top_contrast).mark_bar().encode(
    x=alt.X("salience_score:Q", title="Directional Salience (std_diff * log10(support))", axis=alt.Axis(format=".2f")),
    y=alt.Y("narrative frame:N",
            sort=alt.SortField(field="abs_salience", order="descending"),
            axis=alt.Axis(labelLimit=0, labelOverlap=False),
            title="Frame"),
    color=alt.condition("datum.salience_score > 0", alt.value("#2c7bb6"), alt.value("#d7191c")),
    tooltip=[
        "narrative frame",
        "articles_a:Q", "articles_b:Q",
        alt.Tooltip("prevalence_a:Q", format=".1%"),
        alt.Tooltip("prevalence_b:Q", format=".1%"),
        alt.Tooltip("diff_prevalence:Q", format=".1%"),
        alt.Tooltip("salience_score:Q", format=".2f"),
        "support_articles:Q"
    ]
).properties(title="Top Contrasting Frames (B vs A)", height=height)
st.altair_chart(bar, use_container_width=True)

# Slope chart
long_df = pd.concat([
    top_contrast[["narrative frame", "prevalence_a"]].rename(columns={"prevalence_a": "prevalence"}).assign(period="A"),
    top_contrast[["narrative frame", "prevalence_b"]].rename(columns={"prevalence_b": "prevalence"}).assign(period="B")
], ignore_index=True)

slope = alt.Chart(long_df).mark_line(point=True).encode(
    x=alt.X("period:N", title=None),
    y=alt.Y("prevalence:Q", axis=alt.Axis(format=".0%"), title="Prevalence"),
    detail="narrative frame",
    color=alt.Color("narrative frame:N", legend=None),
    tooltip=["narrative frame", alt.Tooltip("prevalence:Q", format=".1%"), "period"]
).properties(title="Prevalence Shift (A → B)", height=height)
st.altair_chart(slope, use_container_width=True)

with st.expander("Raw Contrast Data"):
    st.dataframe(top_contrast.drop(columns=["abs_salience"]))