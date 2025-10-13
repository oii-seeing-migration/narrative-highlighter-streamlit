# import os
# import streamlit as st
# import altair as alt
# import pandas as pd
# import psycopg
# from psycopg.rows import dict_row
# from dotenv import load_dotenv

# load_dotenv()
# st.set_page_config(page_title="Temporal Dashboard", layout="wide")

# # Sidebar navigation
# st.sidebar.subheader("Navigation")
# try:
#     st.sidebar.page_link("navigation_page.py", label="Navigation Page", icon="🧭")
#     st.sidebar.page_link("pages/01_Narratives_on_Articles.py", label="Narratives on Articles", icon="📰")
#     st.sidebar.page_link("pages/02_Aggregative_Dashboard.py", label="Aggregative Dashboard", icon="📊")
#     st.sidebar.page_link("pages/03_Contrastive_Dashboard.py", label="Contrastive Dashboard", icon="⚖️")
#     st.sidebar.page_link("pages/04_Temporal_Dashboard.py", label="Temporal Dashboard", icon="⏱")
# except Exception:
#     pass

# st.title("Temporal Dashboard")

# # -------------------------------
# # DB config and helpers
# # -------------------------------
# try:
#     DB_URL = st.secrets.get("DATABASE_URL")
# except Exception:
#     DB_URL = os.getenv("DATABASE_URL")

# if not DB_URL:
#     st.error("DATABASE_URL is not configured. Set it in .env or Streamlit secrets.")
#     st.stop()

# def connect():
#     return psycopg.connect(DB_URL)

# def df_from_query(sql: str, params=()):
#     with connect() as conn, conn.cursor(row_factory=dict_row) as cur:
#         cur.execute("set statement_timeout = '15s'")
#         cur.execute("set application_name = 'temporal_dashboard'")
#         cur.execute(sql, params)
#         rows = cur.fetchall()
#     return pd.DataFrame(rows)

# def _normalize_domains(domains):
#     if not domains:
#         return None
#     return tuple(sorted(set(domains)))

# # Add: axis/scale helper for time ticks
# def _time_axis_and_scale(freq_label: str):
#     if freq_label == "Weekly":
#         axis = alt.Axis(title="Period", format="%b %d, %Y", tickCount={"interval": "week", "step": 1})
#         scale = alt.Scale(nice={"interval": "week", "step": 1})
#     elif freq_label == "Monthly":
#         axis = alt.Axis(title="Period", format="%b %Y", tickCount={"interval": "month", "step": 1})
#         scale = alt.Scale(nice={"interval": "month", "step": 1})
#     else:  # Yearly
#         axis = alt.Axis(title="Period", format="%Y", tickCount={"interval": "year", "step": 1})
#         scale = alt.Scale(nice={"interval": "year", "step": 1})
#     return axis, scale

# # -------------------------------
# # Cached queries
# # -------------------------------
# @st.cache_data(ttl="7d", show_spinner=True)
# def get_date_bounds():
#     sql = """
#       select
#         min(a.pub_date::date) as min_d,
#         max(a.pub_date::date) as max_d
#       from perigon.articles a
#       where exists (
#         select 1
#         from perigon.article_summary_annotations f
#         where f.article_id = a.article_id
#           and f.task = 'frames'
#           and jsonb_typeof(f.annotation_parsed)='array'
#           and jsonb_array_length(f.annotation_parsed) > 0
#       )
#     """
#     df = df_from_query(sql)
#     if df.empty:
#         return None, None
#     return df.loc[0, "min_d"], df.loc[0, "max_d"]

# @st.cache_data(ttl="7d", show_spinner=True)
# def get_available_domains(start_date, end_date):
#     sql = """
#       select distinct a.source_domain
#       from perigon.articles a
#       where a.pub_date::date between %s and %s
#         and exists (
#           select 1
#           from perigon.article_summary_annotations f
#           where f.article_id = a.article_id
#             and f.task = 'frames'
#             and jsonb_typeof(f.annotation_parsed)='array'
#             and jsonb_array_length(f.annotation_parsed) > 0
#         )
#       order by 1
#     """
#     df = df_from_query(sql, (start_date, end_date))
#     return df["source_domain"].tolist() if not df.empty else []

# @st.cache_data(ttl="7d", show_spinner=True)
# def get_frames_time_series(start_date, end_date, freq_unit: str, source_domains=None):
#     """
#     freq_unit: one of ('week','month','year') mapped from UI.
#     Returns: period (date), narrative frame, articles, prevalence
#     """
#     # Sanitize freq_unit to allowed tokens to avoid SQL injection
#     freq_unit = {"Weekly": "week", "Monthly": "month", "Yearly": "year"}[freq_unit]

#     domains = _normalize_domains(source_domains)
#     params = [start_date, end_date]

#     # Dynamic domain filter
#     domain_where = ""
#     if domains:
#         domain_where = " and b.source_domain = any(%s) "
#         params.append(list(domains))

#     sql = f"""
#       with base as (
#         select a.article_id, a.pub_date, a.source_domain
#         from perigon.articles a
#         where a.pub_date::date between %s and %s
#       ),
#       frames_exploded as (
#         select
#           date_trunc('{freq_unit}', b.pub_date)::date as period,
#           b.article_id,
#           fr.frame
#         from base b
#         join perigon.article_summary_annotations f
#           on f.article_id = b.article_id
#          and f.task = 'frames'
#          and jsonb_typeof(f.annotation_parsed)='array'
#          and jsonb_array_length(f.annotation_parsed) > 0
#         cross join lateral jsonb_array_elements_text(f.annotation_parsed) as fr(frame)
#         where true
#         {domain_where}
#       ),
#       totals as (
#         select period, count(distinct article_id) as total
#         from frames_exploded
#         group by period
#       )
#       select
#         fe.period,
#         fe.frame as "narrative frame",
#         count(distinct fe.article_id) as articles,
#         (count(distinct fe.article_id)::float / t.total) as prevalence
#       from frames_exploded fe
#       join totals t on t.period = fe.period
#       group by fe.period, fe.frame, t.total
#       order by fe.period, articles desc
#     """
#     df = df_from_query(sql, tuple(params))
#     if not df.empty:
#         df["period"] = pd.to_datetime(df["period"])
#     return df

# # -------------------------------
# # UI controls
# # -------------------------------
# min_dt, max_dt = get_date_bounds()
# if not min_dt or not max_dt:
#     st.error("No frame-annotated articles found.")
#     st.stop()

# st.sidebar.header("Temporal Settings")
# freq = st.sidebar.selectbox("Granularity", ["Weekly", "Monthly", "Yearly"], index=0)

# picked = st.sidebar.date_input(
#     "Date range",
#     value=(min_dt, max_dt),
#     min_value=min_dt,
#     max_value=max_dt
# )
# if isinstance(picked, tuple) and len(picked) == 2:
#     start_date, end_date = picked
# else:
#     start_date = end_date = picked

# # Domain filter
# available_domains = get_available_domains(start_date, end_date)
# selected_domains = st.sidebar.multiselect(
#     "Source domain",
#     options=available_domains,
#     default=available_domains,
# )

# # -------------------------------
# # Load time series
# # -------------------------------
# ts = get_frames_time_series(start_date, end_date, freq, selected_domains)
# if ts.empty:
#     st.info("No data in selected range.")
#     st.stop()

# # Top frames overall to help select
# overall = (
#     ts.groupby("narrative frame")["articles"]
#       .sum().sort_values(ascending=False).head(30).index.tolist()
# )

# selected_frames = st.multiselect(
#     "Select frames (empty = top 8 auto)",
#     options=overall,
#     default=overall[:8]
# )
# if not selected_frames:
#     selected_frames = overall[:8]

# plot_df = ts[ts["narrative frame"].isin(selected_frames)].copy()

# # -------------------------------
# # Charts
# # -------------------------------
# axis_x, scale_x = _time_axis_and_scale(freq)

# line = alt.Chart(plot_df).mark_line(point=True).encode(
#     x=alt.X("period:T", axis=axis_x, scale=scale_x),
#     y=alt.Y("prevalence:Q", axis=alt.Axis(format=".0%"), title="Prevalence"),
#     color=alt.Color("narrative frame:N", title="Frame"),
#     tooltip=[
#         alt.Tooltip("narrative frame:N", title="Frame"),
#         alt.Tooltip("period:T", title="Period"),
#         alt.Tooltip("articles:Q", title="# Articles"),
#         alt.Tooltip("prevalence:Q", format=".1%", title="Prevalence"),
#     ]
# ).properties(title=f"Frame Prevalence Over Time ({freq})")
# st.altair_chart(line, use_container_width=True)

# area = alt.Chart(plot_df).mark_area(interpolate="monotone").encode(
#     x=alt.X("period:T", axis=axis_x, scale=scale_x),
#     y=alt.Y("prevalence:Q", stack="normalize", axis=alt.Axis(format=".0%"), title="Share (selected frames)"),
#     color=alt.Color("narrative frame:N", title="Frame"),
#     tooltip=[
#         alt.Tooltip("narrative frame:N", title="Frame"),
#         alt.Tooltip("period:T", title="Period"),
#         alt.Tooltip("prevalence:Q", format=".1%", title="Prevalence"),
#     ]
# ).properties(title="Relative Share (Selected Frames)")
# st.altair_chart(area, use_container_width=True)

# with st.expander("Underlying Time Series Data"):
#     st.dataframe(plot_df.sort_values(["period", "narrative frame"]))




import os
import streamlit as st
import altair as alt
import pandas as pd

st.set_page_config(page_title="Temporal Dashboard", layout="wide")

# # Sidebar navigation
# st.sidebar.subheader("Navigation")
# try:
#     st.sidebar.page_link("navigation_page.py", label="Navigation Page", icon="🧭")
#     st.sidebar.page_link("pages/01_Narratives_on_Articles.py", label="Narratives on Articles", icon="📰")
#     st.sidebar.page_link("pages/02_Aggregative_Dashboard.py", label="Aggregative Dashboard", icon="📊")
#     st.sidebar.page_link("pages/03_Contrastive_Dashboard.py", label="Contrastive Dashboard", icon="⚖️")
#     st.sidebar.page_link("pages/04_Temporal_Dashboard.py", label="Temporal Dashboard", icon="⏱")
# except Exception:
#     pass

st.title("Temporal Dashboard")

# -------------------------------------
# Load precomputed aggregates (Parquet)
# -------------------------------------
DATA_DIR = os.path.expanduser("./data")
STANCE_PATH = os.path.join(DATA_DIR, "stance_daily.parquet")
FRAMES_PATH = os.path.join(DATA_DIR, "frames_daily.parquet")
MESO_PATH   = os.path.join(DATA_DIR, "meso_daily.parquet")  # not used directly here

@st.cache_data(ttl="1h", show_spinner=True)
def load_parquets(stance_fp: str, frames_fp: str, meso_fp: str):
    def _read_parquet(fp):
        if not os.path.exists(fp):
            return pd.DataFrame()
        df = pd.read_parquet(fp)
        if "day" in df.columns:
            df["day"] = pd.to_datetime(df["day"], errors="coerce")
        for col in ("source_domain", "model"):
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)
        if "count" in df.columns:
            df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
        return df

    stance_df = _read_parquet(stance_fp)
    frames_df = _read_parquet(frames_fp)
    meso_df   = _read_parquet(meso_fp)
    return stance_df, frames_df, meso_df

stance_df, frames_df, _ = load_parquets(STANCE_PATH, FRAMES_PATH, MESO_PATH)

if stance_df.empty and frames_df.empty:
    st.error(f"No aggregates found in {DATA_DIR}. Ensure stance_daily.parquet and frames_daily.parquet exist.")
    st.stop()

# -------------------------------------
# Helpers
# -------------------------------------
def _time_axis_and_scale(freq_label: str):
    if freq_label == "Weekly":
        axis = alt.Axis(title="Period", format="%b %d, %Y", tickCount={"interval": "week", "step": 1})
        scale = alt.Scale(nice={"interval": "week", "step": 1})
    elif freq_label == "Monthly":
        axis = alt.Axis(title="Period", format="%b %Y", tickCount={"interval": "month", "step": 1})
        scale = alt.Scale(nice={"interval": "month", "step": 1})
    else:  # Yearly
        axis = alt.Axis(title="Period", format="%Y", tickCount={"interval": "year", "step": 1})
        scale = alt.Scale(nice={"interval": "year", "step": 1})
    return axis, scale

def _freq_to_pandas(freq_label: str) -> str:
    # Use pandas-supported period codes:
    # - Weekly anchored to Monday
    # - Monthly period ('M')
    # - Yearly period ('A-DEC')
    return {"Weekly": "W-MON", "Monthly": "M", "Yearly": "A-DEC"}[freq_label]

def add_period(df: pd.DataFrame, freq_label: str) -> pd.DataFrame:
    if df.empty or "day" not in df.columns:
        return df
    freq = _freq_to_pandas(freq_label)
    out = df.copy()
    # Convert to Period, then to start-of-period Timestamp (avoids 'MS' unsupported error)
    out["period"] = out["day"].dt.to_period(freq).dt.start_time
    return out

def available_models_union(*dfs):
    models = set()
    for df in dfs:
        if not df.empty and "model" in df.columns:
            models.update(df["model"].dropna().unique().tolist())
    return sorted([m for m in models if m])

# -------------------------------------
# Sidebar controls (Model, Time, Domain)
# -------------------------------------
# Model selector
models = available_models_union(stance_df, frames_df)
default_model = "Qwen3-32B" if "Qwen3-32B" in models else (models[0] if models else None)
if not models:
    st.error("No models found in aggregates.")
    st.stop()
selected_model = st.sidebar.selectbox("Model", options=models, index=models.index(default_model) if default_model in models else 0)

# Date bounds across selected model
def model_filter(df):
    if df.empty or "model" not in df.columns:
        return df
    return df[df["model"] == selected_model].copy()

stance_m = model_filter(stance_df)
frames_m = model_filter(frames_df)

date_series = []
for df in (stance_m, frames_m):
    if not df.empty and "day" in df.columns:
        date_series.append(df["day"])
if date_series:
    all_days = pd.concat(date_series).dropna()
    min_dt, max_dt = all_days.min().date(), all_days.max().date()
else:
    st.error("No valid 'day' column found for the selected model.")
    st.stop()

# Granularity
freq_label = st.sidebar.selectbox("Granularity", ["Weekly", "Monthly", "Yearly"], index=0)

# Date picker
picked = st.sidebar.date_input("Date range", value=(min_dt, max_dt), min_value=min_dt, max_value=max_dt)
if isinstance(picked, tuple) and len(picked) == 2:
    start_date, end_date = picked
else:
    start_date = end_date = picked

def date_filter(df: pd.DataFrame):
    if df.empty or "day" not in df.columns:
        return df
    return df[(df["day"].dt.date >= start_date) & (df["day"].dt.date <= end_date)].copy()

stance_f = date_filter(stance_m)
frames_f = date_filter(frames_m)

# Domain filter (defaults to all domains in filtered range)
domains = set()
for df in (stance_f, frames_f):
    if not df.empty and "source_domain" in df.columns:
        domains.update(df["source_domain"].dropna().unique().tolist())
domains = sorted([d for d in domains if d])
selected_domains = st.sidebar.multiselect("Source domain", options=domains, default=domains)

def domain_filter(df: pd.DataFrame):
    if df.empty or not selected_domains or "source_domain" not in df.columns:
        return df
    return df[df["source_domain"].isin(selected_domains)].copy()

stance_f = domain_filter(stance_f)
frames_f = domain_filter(frames_f)

# Add period column post-filter
stance_p = add_period(stance_f, freq_label)
frames_p = add_period(frames_f, freq_label)

# -------------------------------------
# Build denominators (total relevant per period)
# -------------------------------------
# Total relevant articles per period from stance counts (sum across labels)
if not stance_p.empty:
    totals_per_period = (
        stance_p.groupby("period", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "total"})
    )
else:
    totals_per_period = pd.DataFrame(columns=["period", "total"])

# -------------------------------------
# Frames: temporal prevalence lines
# -------------------------------------
if frames_p.empty or totals_per_period.empty:
    st.info("No frame data in selected filters.")
else:
    frames_counts = (
        frames_p.groupby(["period", "frame"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
    frames_ts = frames_counts.merge(totals_per_period, on="period", how="left")
    frames_ts["prevalence"] = frames_ts.apply(
        lambda r: (r["articles"] / r["total"]) if r["total"] and r["total"] > 0 else 0.0, axis=1
    )

    # Top frames overall in the window to drive selection
    overall_frames = (
        frames_ts.groupby("frame")["articles"]
        .sum()
        .sort_values(ascending=False)
        .head(30)
        .index.tolist()
    )
    selected_frames = st.multiselect(
        "Select frames (empty = top 8 auto)",
        options=overall_frames,
        default=overall_frames[:8]
    )
    if not selected_frames:
        selected_frames = overall_frames[:8]

    plot_frames = frames_ts[frames_ts["frame"].isin(selected_frames)].copy()

    axis_x, scale_x = _time_axis_and_scale(freq_label)
    line = alt.Chart(plot_frames).mark_line(point=True).encode(
        x=alt.X("period:T", axis=axis_x, scale=scale_x),
        y=alt.Y("prevalence:Q", axis=alt.Axis(format=".0%"), title="Prevalence"),
        color=alt.Color("frame:N", title="Frame"),
        tooltip=[
            alt.Tooltip("frame:N", title="Frame"),
            alt.Tooltip("period:T", title="Period"),
            alt.Tooltip("articles:Q", title="# Articles"),
            alt.Tooltip("prevalence:Q", format=".1%", title="Prevalence"),
        ]
    ).properties(title=f"Frame Prevalence Over Time ({freq_label}, Model: {selected_model})")
    st.altair_chart(line, use_container_width=True)

# -------------------------------------
# Stance: temporal stance-score lines (by domain)
# Score = (OPEN - RESTRICTIVE) / (OPEN + RESTRICTIVE + NEUTRAL)
# -------------------------------------
st.subheader("Stance Toward Migration Over Time (by Domain)")
if stance_p.empty:
    st.info("No stance data in selected filters.")
else:
    # Sum per period x domain x stance
    stance_sum = (
        stance_p.groupby(["period", "source_domain", "stance"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
    # Pivot to OPEN/RESTRICTIVE/NEUTRAL columns
    pivot = stance_sum.pivot_table(
        index=["period", "source_domain"],
        columns="stance",
        values="articles",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    for col in ["OPEN", "RESTRICTIVE", "NEUTRAL"]:
        if col not in pivot.columns:
            pivot[col] = 0

    pivot["total"] = pivot["OPEN"] + pivot["RESTRICTIVE"] + pivot["NEUTRAL"]
    pivot["stance_score"] = pivot.apply(
        lambda r: (r["OPEN"] - r["RESTRICTIVE"]) / r["total"] if r["total"] > 0 else None, axis=1
    )
    stance_ts = pivot.dropna(subset=["stance_score"]).copy()

    # Keep only selected domains (already filtered, but safe)
    if selected_domains:
        stance_ts = stance_ts[stance_ts["source_domain"].isin(selected_domains)].copy()

    if stance_ts.empty:
        st.info("No stance series to plot after filtering.")
    else:
        axis_x, scale_x = _time_axis_and_scale(freq_label)
        stance_line = alt.Chart(stance_ts).mark_line(point=True).encode(
            x=alt.X("period:T", axis=axis_x, scale=scale_x),
            y=alt.Y("stance_score:Q", title="Stance Score", scale=alt.Scale(domain=(-1, 1), clamp=True)),
            color=alt.Color("source_domain:N", title="Domain"),
            tooltip=[
                alt.Tooltip("source_domain:N", title="Domain"),
                alt.Tooltip("period:T", title="Period"),
                alt.Tooltip("stance_score:Q", title="Score", format=".2f"),
                alt.Tooltip("OPEN:Q", title="OPEN"),
                alt.Tooltip("RESTRICTIVE:Q", title="RESTRICTIVE"),
                alt.Tooltip("NEUTRAL:Q", title="NEUTRAL"),
                alt.Tooltip("total:Q", title="Total"),
            ],
        ).properties(title=f"Stance Score Over Time ({freq_label}, Model: {selected_model})", height=420)
        st.altair_chart(stance_line, use_container_width=True)

with st.expander("Underlying Data Snapshots"):
    st.write("Frames (filtered):", frames_f.head(1000))
    st.write("Stance (filtered):", stance_f.head(1000))