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
top_n = st.sidebar.slider("Top N frames (by |difference|)", 5, 40, 20, 1)

contrast_df, agg_a, agg_b = compute_frame_contrast(df, period_a, period_b, min_articles_total=min_support)

st.caption(f"Period A: {period_a[0]} → {period_a[1]} | Period B: {period_b[0]} → {period_b[1]}")

if contrast_df.empty:
    st.info("No frames pass support threshold.")
    st.stop()

# --------------------------------------------------------------------
# Diverging Bar Chart (replace previous salience bar)
# Rank by absolute percentage point difference in prevalence
# --------------------------------------------------------------------
contrast_df["abs_diff"] = contrast_df["diff_prevalence"].abs()
top_contrast = contrast_df.sort_values("abs_diff", ascending=False).head(top_n).copy()

# Prepare long-form with signed values (A goes left / negative, B goes right / positive)
plot_df = top_contrast[["narrative frame", "prevalence_a", "prevalence_b", "diff_prevalence"]].copy()
plot_df = plot_df.melt(
    id_vars=["narrative frame", "diff_prevalence"],
    value_vars=["prevalence_a", "prevalence_b"],
    var_name="period_var",
    value_name="prevalence"
)
plot_df["period"] = plot_df["period_var"].map({"prevalence_a": "A", "prevalence_b": "B"})
plot_df["signed_prevalence"] = plot_df.apply(
    lambda r: -r["prevalence"] if r["period"] == "A" else r["prevalence"], axis=1
)

# Order frames from most A‑associated to most B‑associated (diff_prevalence ascending)
frame_order = plot_df.drop_duplicates("narrative frame") \
                     .sort_values("diff_prevalence")["narrative frame"].tolist()

max_val = plot_df["prevalence"].max()
x_limit = float((max_val * 1.15) if max_val > 0 else 0.05)

bar = alt.Chart(plot_df).mark_bar().encode(
    x=alt.X("signed_prevalence:Q",
            title="Prevalence (% of articles)  A ◀        ▶ B",
            scale=alt.Scale(domain=[-x_limit, x_limit], nice=False),
            axis=alt.Axis(format=".0%")),
    y=alt.Y("narrative frame:N",
            sort=frame_order,
            axis=alt.Axis(labelLimit=0, labelOverlap=False),
            title="Frame"),
    color=alt.Color("period:N",
                    title="Period",
                    scale=alt.Scale(domain=["A", "B"], range=["#d7191c", "#2c7bb6"])),
    tooltip=[
        "narrative frame",
        alt.Tooltip("period:N", title="Period"),
        alt.Tooltip("prevalence:Q", title="Prevalence", format=".1%"),
        alt.Tooltip("diff_prevalence:Q", title="B - A (pp)", format=".1%")
    ]
).properties(
    title="Diverging Usage of Narrative Frames (Period A vs Period B)",
    height=max(26 * len(frame_order), 320)
)

# Center difference labels (percentage point diff) near x=0
diff_labels = top_contrast[["narrative frame", "diff_prevalence"]].copy()
diff_labels["pp_diff"] = diff_labels["diff_prevalence"] * 100  # percentage points

text_layer = alt.Chart(diff_labels).mark_text(
    fontSize=11,
    fontWeight="bold",
    dx=0
).encode(
    x=alt.value(bar.properties().width or 0),  # placeholder (will be overridden by transform)
    y=alt.Y("narrative frame:N", sort=frame_order),
    text=alt.Text("pp_diff:Q", format="+.1f"),
    color=alt.value("#444")
).transform_calculate(
    # Place text at 0 (center); Vega-Lite expression sets x to 0 value on scale
    signed_prevalence="0"
).encode(
    x=alt.X("signed_prevalence:Q", scale=alt.Scale(domain=[-x_limit, x_limit], nice=False), axis=alt.Axis(labels=False))
)

diverging_chart = bar  # (Optional to add center text: bar + text_layer)

st.altair_chart(diverging_chart, use_container_width=True)

st.markdown(
    "*Left (red) bars represent Period A; right (blue) bars represent Period B. Frames ordered from most A‑associated (negative difference) to most B‑associated (positive). Differences shown in percentage points (B - A).*"
)


with st.expander("Raw Contrast Data"):
    st.dataframe(top_contrast[[
        "narrative frame",
        "articles_a", "articles_b",
        "prevalence_a", "prevalence_b",
        "diff_prevalence",
        "abs_diff",
        "salience_score",  # retained for reference
        "support_articles"
    ]])