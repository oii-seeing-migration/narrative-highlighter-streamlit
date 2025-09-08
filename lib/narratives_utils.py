import pandas as pd
import numpy as np
import ast
import unicodedata
import re
from functools import lru_cache
import streamlit as st

# -----------------------------
# Canonicalization
# -----------------------------
def _canon(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = unicodedata.normalize("NFKC", str(s)).replace("\u00A0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

# -----------------------------
# Data Loading
# -----------------------------
@st.cache_data(show_spinner=True)
def load_data(csv_path: str = "data/GuardianCorpus_Vahid_AI_Annotated.csv"):
    df = pd.read_csv(csv_path)
    if "date" in df.columns:
        df["date_dt"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    else:
        df["date_dt"] = pd.NaT

    # Parse meso dict
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

    df = df.reset_index(drop=False).rename(columns={"index": "doc_id"})
    return df

# -----------------------------
# Explode
# -----------------------------
def explode_mesos(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.copy()
    tmp["results"] = tmp["classification_Meso_Qwen3-32B"].apply(
        lambda d: d.get("results", []) if isinstance(d, dict) else []
    )
    ex = tmp.explode("results", ignore_index=True)
    ex["narrative frame"] = ex["results"].apply(lambda r: (r or {}).get("narrative frame"))
    ex["meso narrative"] = ex["results"].apply(lambda r: (r or {}).get("meso narrative"))
    ex["text fragment"] = ex["results"].apply(lambda r: (r or {}).get("text fragment"))

    ex["narrative frame"] = ex["narrative frame"].apply(_canon)
    ex["meso narrative"] = ex["meso narrative"].apply(_canon)
    return ex.drop(columns=["results"])

# -----------------------------
# Aggregation for a range
# -----------------------------
def aggregate_range(df_range: pd.DataFrame):
    ex = explode_mesos(df_range)
    total_articles = df_range["doc_id"].nunique()

    # Frame-level
    f_articles = (
        ex[ex["narrative frame"] != ""]
        .groupby("narrative frame")["doc_id"].nunique()
        .rename("articles").reset_index()
    )
    f_frag = (
        ex[ex["narrative frame"] != ""]
        .groupby("narrative frame")
        .size().rename("fragments").reset_index()
    )
    frames_summary = f_articles.merge(f_frag, on="narrative frame", how="outer").fillna(0)
    frames_summary["prevalence"] = frames_summary["articles"] / max(total_articles, 1)
    frames_summary["intensity"] = frames_summary.apply(
        lambda r: r["fragments"] / r["articles"] if r["articles"] > 0 else 0, axis=1
    )
    frames_summary = frames_summary.sort_values(["articles", "fragments"], ascending=False).reset_index(drop=True)

    # Meso overall
    m_articles = (
        ex[ex["meso narrative"] != ""]
        .groupby("meso narrative")["doc_id"].nunique()
        .rename("articles").reset_index()
    )
    m_frag = (
        ex[ex["meso narrative"] != ""]
        .groupby("meso narrative")
        .size().rename("fragments").reset_index()
    )
    meso_summary = m_articles.merge(m_frag, on="meso narrative", how="outer").fillna(0)
    meso_summary["prevalence"] = meso_summary["articles"] / max(total_articles, 1)
    meso_summary["intensity"] = meso_summary.apply(
        lambda r: r["fragments"] / r["articles"] if r["articles"] > 0 else 0, axis=1
    )
    meso_summary = meso_summary.sort_values(["articles", "fragments"], ascending=False).reset_index(drop=True)

    return {
        "total_articles": int(total_articles),
        "frames_summary": frames_summary,
        "meso_summary": meso_summary,
        "exploded": ex,
    }

# -----------------------------
# Contrast
# -----------------------------
def compute_frame_contrast(df_full: pd.DataFrame,
                           period_a: tuple,
                           period_b: tuple,
                           min_articles_total: int = 3):
    (a_start, a_end), (b_start, b_end) = period_a, period_b
    a_mask = (df_full["date_dt"].dt.date >= a_start) & (df_full["date_dt"].dt.date <= a_end)
    b_mask = (df_full["date_dt"].dt.date >= b_start) & (df_full["date_dt"].dt.date <= b_end)
    df_a = df_full[a_mask].copy()
    df_b = df_full[b_mask].copy()
    agg_a = aggregate_range(df_a)
    agg_b = aggregate_range(df_b)
    n_a = max(agg_a["total_articles"], 1)
    n_b = max(agg_b["total_articles"], 1)

    fa = agg_a["frames_summary"][["narrative frame", "articles", "prevalence"]].rename(
        columns={"articles": "articles_a", "prevalence": "prevalence_a"}
    )
    fb = agg_b["frames_summary"][["narrative frame", "articles", "prevalence"]].rename(
        columns={"articles": "articles_b", "prevalence": "prevalence_b"}
    )
    merged = fa.merge(fb, on="narrative frame", how="outer").fillna(0)
    merged["diff_prevalence"] = merged["prevalence_b"] - merged["prevalence_a"]
    merged["pooled_p"] = (merged["prevalence_a"] * n_a + merged["prevalence_b"] * n_b) / (n_a + n_b)
    denom = np.sqrt(merged["pooled_p"] * (1 - merged["pooled_p"]) * (1 / n_a + 1 / n_b)).replace(0, np.nan)
    merged["std_diff"] = (merged["diff_prevalence"] / denom).fillna(0)
    merged["support_articles"] = merged["articles_a"] + merged["articles_b"]
    merged = merged[merged["support_articles"] >= min_articles_total]
    merged["salience_score"] = merged["std_diff"] * np.log10(merged["support_articles"] + 1)
    merged = merged.sort_values("salience_score", ascending=False).reset_index(drop=True)
    return merged, agg_a, agg_b

# -----------------------------
# Time series (weekly / monthly)
# -----------------------------
def time_series_frames(df: pd.DataFrame, freq: str = "W"):
    # freq: "W" weekly, "M" monthly
    ex = explode_mesos(df[df["date_dt"].notna()])
    if ex.empty:
        return pd.DataFrame(columns=["period", "narrative frame", "articles", "prevalence"])

    ex["period"] = ex["date_dt"].dt.to_period(freq).dt.to_timestamp()
    # Unique articles per frame per period
    grp_articles = (
        ex[ex["narrative frame"] != ""]
        .groupby(["period", "narrative frame"])["doc_id"]
        .nunique().rename("articles").reset_index()
    )
    # Total articles per period
    period_tot = (
        ex.groupby("period")["doc_id"].nunique().rename("total_articles").reset_index()
    )
    out = grp_articles.merge(period_tot, on="period", how="left")
    out["prevalence"] = out["articles"] / out["total_articles"].replace(0, 1)
    return out.sort_values(["period", "prevalence"], ascending=[True, False]).reset_index(drop=True)