import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import ast

# -----------------------------
# Data loading and helpers
# -----------------------------
@st.cache_data(show_spinner=True)
def load_data():
    data_file_name = "GuardianCorpus_Vahid"
    df = pd.read_csv(f"data/{data_file_name}_AI_Annotated.csv")
    # Parse date
    if "date" in df.columns:
        df["date_dt"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    else:
        df["date_dt"] = pd.NaT

    # Ensure meso column is a dict with 'results'
    def _parse_mesos(val):
        if isinstance(val, dict):
            return val
        try:
            d = ast.literal_eval(val)
            if isinstance(d, dict):
                return d
        except Exception:
            pass
        return {"results": []}

    if "classification_Meso_Qwen3-32B" in df.columns:
        df["classification_Meso_Qwen3-32B"] = df["classification_Meso_Qwen3-32B"].apply(_parse_mesos)
    else:
        df["classification_Meso_Qwen3-32B"] = {"results": []}

    # Stable document id
    df = df.reset_index(drop=False).rename(columns={"index": "doc_id"})
    return df


def explode_mesos(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.copy()
    tmp["results"] = tmp["classification_Meso_Qwen3-32B"].apply(
        lambda d: d.get("results", []) if isinstance(d, dict) else []
    )
    ex = tmp.explode("results", ignore_index=True)
    ex["narrative frame"] = ex["results"].apply(lambda r: (r or {}).get("narrative frame"))
    ex["meso narrative"] = ex["results"].apply(lambda r: (r or {}).get("meso narrative"))
    ex["text fragment"] = ex["results"].apply(lambda r: (r or {}).get("text fragment"))
    return ex.drop(columns=["results"])


def aggregate_range(df_range: pd.DataFrame):
    # Explode meso annotations
    ex = explode_mesos(df_range)

    total_articles = df_range["doc_id"].nunique()

    # Frames: unique articles and total fragments
    frames_article = (
        ex.dropna(subset=["narrative frame"])
          .groupby("narrative frame")["doc_id"].nunique()
          .rename("articles").reset_index()
    )
    frames_fragments = (
        ex.dropna(subset=["narrative frame"])
          .groupby("narrative frame")
          .size().rename("fragments").reset_index()
    )
    frames_summary = frames_article.merge(frames_fragments, on="narrative frame", how="outer").fillna(0)
    frames_summary["prevalence"] = frames_summary["articles"] / max(total_articles, 1)
    frames_summary["intensity"] = frames_summary.apply(
        lambda r: (r["fragments"] / r["articles"]) if r["articles"] > 0 else 0, axis=1
    )
    frames_summary = frames_summary.sort_values(["articles", "fragments"], ascending=False).reset_index(drop=True)

    # Meso: overall (not per-frame)
    meso_article = (
        ex.dropna(subset=["meso narrative"])
          .groupby("meso narrative")["doc_id"].nunique()
          .rename("articles").reset_index()
    )
    meso_fragments = (
        ex.dropna(subset=["meso narrative"])
          .groupby("meso narrative")
          .size().rename("fragments").reset_index()
    )
    meso_summary = meso_article.merge(meso_fragments, on="meso narrative", how="outer").fillna(0)
    meso_summary = meso_summary.sort_values(["articles", "fragments"], ascending=False).reset_index(drop=True)

    return {
        "total_articles": int(total_articles),
        "frames_summary": frames_summary,
        "meso_summary": meso_summary,
    }


# -----------------------------
# UI
# -----------------------------
st.title("Dataset Overview")

df = load_data()

# Sidebar controls
st.sidebar.header("Overview Filters")

# Date range picker
dates = df["date_dt"].dropna()
if dates.empty:
    st.warning("No valid dates found in the dataset. Showing all data.")
    start_date = None
    end_date = None
else:
    min_dt = dates.min().date()
    max_dt = dates.max().date()
    default_range = (min_dt, max_dt)
    picked = st.sidebar.date_input(
        "Date range",
        value=default_range,
        min_value=min_dt,
        max_value=max_dt,
    )
    # date_input returns a single date or a tuple
    if isinstance(picked, tuple) and len(picked) == 2:
        start_date, end_date = picked
    else:
        start_date = picked
        end_date = picked

# Filter by selected date range
if start_date and end_date:
    mask = (df["date_dt"].dt.date >= start_date) & (df["date_dt"].dt.date <= end_date)
    df_range = df[mask].copy()
else:
    df_range = df.copy()

# Summary counters
st.write(f"Articles in selected range: {df_range['doc_id'].nunique()}")

# Aggregate and visualize
agg = aggregate_range(df_range)

if agg["total_articles"] == 0:
    st.info("No articles in the selected date range.")
else:
    # Top Frames (by # articles)
    st.subheader("Top Frames")
    frames_top = agg["frames_summary"].head(20)
    frames_height = max(24 * len(frames_top), 360)  # ~24px per category
    frames_chart = alt.Chart(frames_top).mark_bar().encode(
        x=alt.X("articles:Q", title="# Articles"),
        y=alt.Y(
            "narrative frame:N",
            sort="-x",
            title="Frame",
            axis=alt.Axis(labelLimit=0, labelOverlap=False)  # do not hide any labels
        ),
        tooltip=["articles:Q", "fragments:Q", alt.Tooltip("prevalence:Q", format=".0%"), "intensity:Q"],
    ).properties(height=frames_height)
    st.altair_chart(frames_chart, use_container_width=True)

    # Top Meso Narratives (by # articles)
    st.subheader("Top Meso Narratives")
    meso_top = agg["meso_summary"].head(20)
    meso_height = max(24 * len(meso_top), 360)
    meso_chart = alt.Chart(meso_top).mark_bar().encode(
        x=alt.X("articles:Q", title="# Articles"),
        y=alt.Y(
            "meso narrative:N",
            sort="-x",
            title="Meso narrative",
            axis=alt.Axis(
                labelLimit=0,
                labelOverlap=False,
                titleAngle=270,     # vertical on the left
                titlePadding=120,    # push title away from labels
                labelPadding=6
            )
        ),
        tooltip=["articles:Q", "fragments:Q"],
    ).properties(height=meso_height)
    st.altair_chart(meso_chart, use_container_width=True)
