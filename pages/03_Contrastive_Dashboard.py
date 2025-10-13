# import os
# import streamlit as st
# import altair as alt
# import pandas as pd
# import psycopg
# from psycopg.rows import dict_row
# from dotenv import load_dotenv

# load_dotenv()

# st.set_page_config(page_title="Contrastive Dashboard", layout="wide")

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

# st.title("Contrastive Dashboard")

# # -------------------------------------------------
# # DB config
# # -------------------------------------------------
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
#         cur.execute("set application_name = 'contrastive_dashboard'")
#         cur.execute(sql, params)
#         rows = cur.fetchall()
#     return pd.DataFrame(rows)

# def _normalize_domains(domains):
#     if not domains:
#         return None
#     return tuple(sorted(set(domains)))

# # -------------------------------------------------
# # Cached DB queries
# # -------------------------------------------------
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
#           and jsonb_typeof(f.annotation_parsed) = 'array'
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
#             and jsonb_typeof(f.annotation_parsed) = 'array'
#             and jsonb_array_length(f.annotation_parsed) > 0
#         )
#       order by 1
#     """
#     df = df_from_query(sql, (start_date, end_date))
#     return df["source_domain"].tolist() if not df.empty else []

# @st.cache_data(ttl="7d", show_spinner=True)
# def get_total_annotated_articles(start_date, end_date, source_domains=None):
#     source_domains = _normalize_domains(source_domains)
#     sql = """
#       select count(distinct a.article_id) as total
#       from perigon.articles a
#       where a.pub_date::date between %s and %s
#         and exists (
#           select 1
#           from perigon.article_summary_annotations f
#           where f.article_id = a.article_id
#             and f.task = 'frames'
#             and jsonb_typeof(f.annotation_parsed) = 'array'
#             and jsonb_array_length(f.annotation_parsed) > 0
#         )
#     """
#     params = [start_date, end_date]
#     if source_domains:
#         sql += " and a.source_domain = any(%s)"
#         params.append(list(source_domains))
#     df = df_from_query(sql, tuple(params))
#     return int(df.loc[0, "total"]) if not df.empty else 0

# @st.cache_data(ttl="7d", show_spinner=True)
# def get_frames_counts(start_date, end_date, source_domains=None):
#     source_domains = _normalize_domains(source_domains)
#     sql = """
#       select
#         fr.frame as "narrative frame",
#         count(distinct a.article_id) as articles
#       from perigon.articles a
#       join perigon.article_summary_annotations f
#         on f.article_id = a.article_id
#        and f.task = 'frames'
#        and jsonb_typeof(f.annotation_parsed) = 'array'
#        and jsonb_array_length(f.annotation_parsed) > 0
#       cross join lateral jsonb_array_elements_text(f.annotation_parsed) as fr(frame)
#       where a.pub_date::date between %s and %s
#     """
#     params = [start_date, end_date]
#     if source_domains:
#         sql += " and a.source_domain = any(%s)"
#         params.append(list(source_domains))
#     sql += """
#       group by fr.frame
#       order by articles desc
#     """
#     return df_from_query(sql, tuple(params))

# # -------------------------------------------------
# # Contrast computation (separate filters 1 and 2)
# # -------------------------------------------------
# def compute_frame_contrast_db(period_1, domains_1, period_2, domains_2, min_articles_total=3):
#     (a_start, a_end) = period_1
#     (b_start, b_end) = period_2

#     total_a = get_total_annotated_articles(a_start, a_end, domains_1)
#     total_b = get_total_annotated_articles(b_start, b_end, domains_2)

#     frames_a = get_frames_counts(a_start, a_end, domains_1).rename(columns={"articles": "articles_1"})
#     frames_b = get_frames_counts(b_start, b_end, domains_2).rename(columns={"articles": "articles_2"})

#     # Keep all frames from both filters; fill missing with zeros
#     contrast = pd.merge(frames_a, frames_b, on="narrative frame", how="outer").fillna(0)
#     contrast["articles_1"] = contrast["articles_1"].astype(int)
#     contrast["articles_2"] = contrast["articles_2"].astype(int)

#     contrast["prevalence_1"] = contrast["articles_1"] / total_a if total_a > 0 else 0.0
#     contrast["prevalence_2"] = contrast["articles_2"] / total_b if total_b > 0 else 0.0

#     contrast["diff_prevalence"] = contrast["prevalence_2"] - contrast["prevalence_1"]
#     contrast["support_articles"] = contrast["articles_1"] + contrast["articles_2"]

#     # Optional support threshold (kept)
#     contrast = contrast[contrast["support_articles"] >= int(min_articles_total)].copy()

#     contrast["salience_score"] = (contrast["support_articles"] * contrast["diff_prevalence"].abs())
#     contrast["abs_diff"] = contrast["diff_prevalence"].abs()

#     agg_1 = frames_a.assign(total_articles=total_a)
#     agg_2 = frames_b.assign(total_articles=total_b)
#     return contrast, agg_1, agg_2

# # -------------------------------------------------
# # Color config (defaults: red & blue)
# # -------------------------------------------------

# COLOR_1 = "#d7191c"
# COLOR_2 = "#2c7bb6"

# def color_header(label: str, color: str):
#     st.sidebar.markdown(
#         f"""
#         <div style="display:flex;align-items:center;gap:8px;margin-top:8px;">
#           <span style="display:inline-block;width:14px;height:14px;background:{color};border:1px solid #999;border-radius:2px;"></span>
#           <strong>{label}</strong>
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )

# # ...existing DB helpers and cached queries...

# # -------------------------------------------------
# # UI controls: Filter (left color) and Filter (right color)
# # -------------------------------------------------
# min_dt, max_dt = get_date_bounds()
# if not min_dt or not max_dt:
#     st.error("No frame-annotated articles found.")
#     st.stop()

# full_range = (min_dt, max_dt)

# # Left filter (COLOR_1)
# color_header("Filter", COLOR_1)
# period_1_in = st.sidebar.date_input("Period", value=full_range, min_value=min_dt, max_value=max_dt, key="period_1")
# def _norm(p):
#     if isinstance(p, tuple) and len(p) == 2:
#         return tuple(sorted(p))
#     return (p, p)
# period_1 = _norm(period_1_in)
# domains_1_options = get_available_domains(period_1[0], period_1[1])
# default_1 = [d for d in domains_1_options if d == "theguardian.com"] or domains_1_options
# domains_1_selected = st.sidebar.multiselect("Source domain", options=domains_1_options, default=default_1, key="domain_1")
# domains_1 = tuple(sorted(set(domains_1_selected))) if domains_1_selected else None

# # Right filter (COLOR_2)
# color_header("Filter", COLOR_2)
# period_2_in = st.sidebar.date_input("Period ", value=full_range, min_value=min_dt, max_value=max_dt, key="period_2")
# period_2 = _norm(period_2_in)
# domains_2_options = get_available_domains(period_2[0], period_2[1])
# default_2 = [d for d in domains_2_options if d == "telegraph.co.uk"] or domains_2_options
# domains_2_selected = st.sidebar.multiselect("Source domain ", options=domains_2_options, default=default_2, key="domain_2")
# domains_2 = tuple(sorted(set(domains_2_selected))) if domains_2_selected else None


# st.sidebar.subheader("Macros")
# min_support = st.sidebar.slider("Min combined article support", 0, 50, 0, 1)
# top_n = st.sidebar.slider("Top N frames (by |difference|)", 5, 40, 20, 1)

# contrast_df, agg_1, agg_2 = compute_frame_contrast_db(period_1, domains_1, period_2, domains_2, min_articles_total=min_support)

# legend_html = f"""
# <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin:6px 0 14px;">
#   <div style="display:flex;align-items:center;gap:6px;">
#     <span style="display:inline-block;width:14px;height:14px;background:{COLOR_1};border:1px solid #999;border-radius:2px;"></span>
#     <span><strong>Filter</strong></span>
#     <span style="color:#666;">{period_1[0]} → {period_1[1]} | Domains: {', '.join(domains_1_selected) if domains_1_selected else 'All'}</span>
#   </div>
#   <div style="display:flex;align-items:center;gap:6px;">
#     <span style="display:inline-block;width:14px;height:14px;background:{COLOR_2};border:1px solid #999;border-radius:2px;"></span>
#     <span><strong>Filter</strong></span>
#     <span style="color:#666;">{period_2[0]} → {period_2[1]} | Domains: {', '.join(domains_2_selected) if domains_2_selected else 'All'}</span>
#   </div>
# </div>
# """
# st.markdown(legend_html, unsafe_allow_html=True)

# if contrast_df.empty:
#     st.info("No frames pass support threshold.")
#     st.stop()

# # --------------------------------------------------------------------
# # Diverging Bar Chart (Left color vs Right color)
# # --------------------------------------------------------------------
# plot_df = contrast_df.copy()
# plot_df["abs_diff"] = plot_df["diff_prevalence"].abs()
# top_contrast = plot_df.sort_values("abs_diff", ascending=False).head(top_n).copy()

# melt_df = top_contrast[["narrative frame", "prevalence_1", "prevalence_2", "diff_prevalence"]].copy().reset_index(drop=True)
# melt_df = melt_df.melt(
#     id_vars=["narrative frame", "diff_prevalence"],
#     value_vars=["prevalence_1", "prevalence_2"],
#     var_name="side_var",
#     value_name="prevalence"
# )
# # Key for encoding; hex for tooltip/legend mapping
# melt_df["side_key"] = melt_df["side_var"].map({"prevalence_1": "LEFT", "prevalence_2": "RIGHT"})
# melt_df["filter_hex"] = melt_df["side_key"].map({"LEFT": COLOR_1, "RIGHT": COLOR_2})
# # Left goes negative, right positive
# melt_df["signed_prevalence"] = melt_df.apply(lambda r: -r["prevalence"] if r["side_key"] == "LEFT" else r["prevalence"], axis=1)

# frame_order = melt_df.drop_duplicates("narrative frame").sort_values("diff_prevalence")["narrative frame"].tolist()
# max_val = melt_df["prevalence"].max()
# x_limit = float((max_val * 1.15) if max_val > 0 else 0.05)

# bar = alt.Chart(melt_df).mark_bar().encode(
#     x=alt.X(
#         "signed_prevalence:Q",
#         title="Prevalence (% of articles)",
#         scale=alt.Scale(domain=[-x_limit, x_limit], nice=False),
#         axis=alt.Axis(format=".0%")
#     ),
#     y=alt.Y("narrative frame:N", sort=frame_order, axis=alt.Axis(labelLimit=0, labelOverlap=False), title="Frame"),
#     color=alt.Color(
#         "side_key:N",
#         title="Filter",
#         scale=alt.Scale(domain=["LEFT", "RIGHT"], range=[COLOR_1, COLOR_2]),
#         # legend=alt.Legend(
#         #     title="Filter",
#         #     symbolType="square",
#         #     labelColor="transparent"  # hide text labels; show only colored squares
#         # ),
#         legend=None,  # hide legend entirely
#     ),
#     tooltip=[
#         alt.Tooltip("narrative frame:N", title="Frame"),
#         alt.Tooltip("filter_hex:N", title="Filter color"),
#         alt.Tooltip("prevalence:Q", title="Prevalence", format=".1%"),
#         alt.Tooltip("diff_prevalence:Q", title="(right - left) pp", format=".1%")
#     ]
# ).properties(
#     # title="Diverging Usage of Narrative Frames (by filter colors)",
#     title="",
#     height=max(26 * len(frame_order), 320)
# )
# st.altair_chart(bar, use_container_width=True)

# with st.expander("Raw Contrast Data"):
#     st.dataframe(top_contrast[[
#         "narrative frame",
#         "prevalence_1", "prevalence_2",
#         "diff_prevalence",
#         "abs_diff",
#         "salience_score",
#         "support_articles"
#     ]])




import os
import streamlit as st
import altair as alt
import pandas as pd

st.set_page_config(page_title="Contrastive Dashboard", layout="wide")

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

st.title("Contrastive Dashboard")

# ------------------------------------------------------------
# Load precomputed aggregates from ./data (no DB round-trips)
# ------------------------------------------------------------
DATA_DIR = os.path.expanduser("./data")
STANCE_PATH = os.path.join(DATA_DIR, "stance_daily.parquet")
FRAMES_PATH = os.path.join(DATA_DIR, "frames_daily.parquet")
MESO_PATH   = os.path.join(DATA_DIR, "meso_daily.parquet")  # not used here

@st.cache_data(ttl="1h", show_spinner=True)
def load_parquets(stance_fp: str, frames_fp: str, meso_fp: str):
    def _read_parquet(fp):
        if not os.path.exists(fp):
            return pd.DataFrame()
        df = pd.read_parquet(fp)
        if "day" in df.columns:
            df["day"] = pd.to_datetime(df["day"], errors="coerce").dt.date
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

if frames_df.empty:
    st.error(f"No frame aggregates found in {FRAMES_PATH}. Generate exports first.")
    st.stop()

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def global_date_bounds(dfs):
    series = []
    for df in dfs:
        if not df.empty and "day" in df.columns:
            series.append(pd.Series(df["day"]))
    if not series:
        return None, None
    all_days = pd.concat(series, ignore_index=True).dropna()
    return all_days.min(), all_days.max()

def _norm_date_input(p):
    if isinstance(p, tuple) and len(p) == 2:
        a, b = p
        return (min(a, b), max(a, b))
    return (p, p)

def pick_domains_for_range(df_frames, df_stance, model, start_date, end_date):
    doms = set()
    for df in (df_frames, df_stance):
        if df.empty:
            continue
        m = df[(df["day"] >= start_date) & (df["day"] <= end_date)]
        if model and "model" in m.columns:
            m = m[m["model"] == model]
        if "source_domain" in m.columns:
            doms.update(m["source_domain"].dropna().unique().tolist())
    return sorted([d for d in doms if d])

def filter_slice(df: pd.DataFrame, model: str, start_date, end_date, domains: set | None):
    if df.empty:
        return df
    m = df[(df["day"] >= start_date) & (df["day"] <= end_date)].copy()
    if model and "model" in m.columns:
        m = m[m["model"] == model]
    if domains and "source_domain" in m.columns:
        m = m[m["source_domain"].isin(domains)].copy()
    return m

def total_articles_from_stance(stance_slice: pd.DataFrame) -> int:
    if stance_slice.empty:
        return 0
    return int(stance_slice["count"].sum())

def frames_counts(frames_slice: pd.DataFrame) -> pd.DataFrame:
    if frames_slice.empty:
        return pd.DataFrame(columns=["narrative frame", "articles"])
    g = (
        frames_slice.groupby("frame", as_index=False)["count"]
        .sum()
        .rename(columns={"frame": "narrative frame", "count": "articles"})
    )
    return g

# ------------------------------------------------------------
# Sidebar controls (Filter A, Filter B, then Macros)
# ------------------------------------------------------------
# Available models (union from stance/frames)
available_models = sorted(set(
    list(frames_df["model"].unique() if "model" in frames_df else []) +
    list(stance_df["model"].unique() if "model" in stance_df else [])
))
if not available_models:
    st.error("No models available in aggregates.")
    st.stop()

min_dt, max_dt = global_date_bounds([frames_df, stance_df])
if not min_dt or not max_dt:
    st.error("No valid 'day' column found in aggregates.")
    st.stop()

# Filter A
st.sidebar.markdown("#### Filter A")
selected_model_A = st.sidebar.selectbox("Model (A)", options=available_models, index=available_models.index("Qwen3-32B") if "Qwen3-32B" in available_models else 0, key="model_a")
period_1_in = st.sidebar.date_input("Period (A)", value=(min_dt, max_dt), min_value=min_dt, max_value=max_dt, key="period_1")
period_1 = _norm_date_input(period_1_in)
domains_1_options = pick_domains_for_range(frames_df, stance_df, selected_model_A, period_1[0], period_1[1])
default_1 = [d for d in domains_1_options if d == "theguardian.com"] or domains_1_options
domains_1_selected = st.sidebar.multiselect("Source domain (A)", options=domains_1_options, default=default_1, key="domain_1")
domains_1 = set(domains_1_selected) if domains_1_selected else None

# Filter B
st.sidebar.markdown("#### Filter B")
selected_model_B = st.sidebar.selectbox("Model (B)", options=available_models, index=available_models.index("Qwen3-32B") if "Qwen3-32B" in available_models else 0, key="model_b")
period_2_in = st.sidebar.date_input("Period (B)", value=(min_dt, max_dt), min_value=min_dt, max_value=max_dt, key="period_2")
period_2 = _norm_date_input(period_2_in)
domains_2_options = pick_domains_for_range(frames_df, stance_df, selected_model_B, period_2[0], period_2[1])
default_2 = [d for d in domains_2_options if d == "telegraph.co.uk"] or domains_2_options
domains_2_selected = st.sidebar.multiselect("Source domain (B)", options=domains_2_options, default=default_2, key="domain_2")
domains_2 = set(domains_2_selected) if domains_2_selected else None

# Macros
st.sidebar.subheader("Macros")
min_support = st.sidebar.slider("Min combined article support", 0, 50, 0, 1)
top_n = st.sidebar.slider("Top N frames (by |difference|)", 5, 40, 20, 1)

# ------------------------------------------------------------
# Compute contrast using aggregates
# ------------------------------------------------------------
stance_a = filter_slice(stance_df, selected_model_A, period_1[0], period_1[1], domains_1)
stance_b = filter_slice(stance_df, selected_model_B, period_2[0], period_2[1], domains_2)
frames_a = filter_slice(frames_df, selected_model_A, period_1[0], period_1[1], domains_1)
frames_b = filter_slice(frames_df, selected_model_B, period_2[0], period_2[1], domains_2)

total_a = total_articles_from_stance(stance_a)
total_b = total_articles_from_stance(stance_b)
frames_a_counts = frames_counts(frames_a).rename(columns={"articles": "articles_1"})
frames_b_counts = frames_counts(frames_b).rename(columns={"articles": "articles_2"})

contrast = pd.merge(frames_a_counts, frames_b_counts, on="narrative frame", how="outer").fillna(0)
if contrast.empty:
    st.info("No frames found for the selected filters.")
    st.stop()

contrast["articles_1"] = contrast["articles_1"].astype(int)
contrast["articles_2"] = contrast["articles_2"].astype(int)
contrast["prevalence_1"] = (contrast["articles_1"] / total_a) if total_a > 0 else 0.0
contrast["prevalence_2"] = (contrast["articles_2"] / total_b) if total_b > 0 else 0.0
contrast["diff_prevalence"] = contrast["prevalence_2"] - contrast["prevalence_1"]
contrast["support_articles"] = contrast["articles_1"] + contrast["articles_2"]
if min_support > 0:
    contrast = contrast[contrast["support_articles"] >= int(min_support)].copy()
if contrast.empty:
    st.info("No frames pass support threshold.")
    st.stop()

# Legend/summary
legend_html = f"""
<div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin:6px 0 14px;">
  <div style="display:flex;align-items:center;gap:6px;">
    <span style="display:inline-block;width:14px;height:14px;background:#d7191c;border:1px solid #999;border-radius:2px;"></span>
    <span><strong>Filter A</strong></span>
    <span style="color:#666;">{period_1[0]} → {period_1[1]} | Domains: {', '.join(sorted(domains_1)) if domains_1 else 'All'} | Model: {selected_model_A}</span>
  </div>
  <div style="display:flex;align-items:center;gap:6px;">
    <span style="display:inline-block;width:14px;height:14px;background:#2c7bb6;border:1px solid #999;border-radius:2px;"></span>
    <span><strong>Filter B</strong></span>
    <span style="color:#666;">{period_2[0]} → {period_2[1]} | Domains: {', '.join(sorted(domains_2)) if domains_2 else 'All'} | Model: {selected_model_B}</span>
  </div>
</div>
"""
st.markdown(legend_html, unsafe_allow_html=True)

# ------------------------------------------------------------
# Diverging bar chart (B minus A)
# ------------------------------------------------------------
plot_df = contrast.copy()
plot_df["abs_diff"] = plot_df["diff_prevalence"].abs()
top_contrast = plot_df.sort_values("abs_diff", ascending=False).head(int(top_n)).copy()

melt_df = top_contrast[["narrative frame", "prevalence_1", "prevalence_2", "diff_prevalence"]].copy().reset_index(drop=True)
melt_df = melt_df.melt(
    id_vars=["narrative frame", "diff_prevalence"],
    value_vars=["prevalence_1", "prevalence_2"],
    var_name="side_var",
    value_name="prevalence"
)
melt_df["side_key"] = melt_df["side_var"].map({"prevalence_1": "A", "prevalence_2": "B"})
melt_df["color_hex"] = melt_df["side_key"].map({"A": "#d7191c", "B": "#2c7bb6"})
melt_df["signed_prev"] = melt_df.apply(lambda r: -r["prevalence"] if r["side_key"] == "A" else r["prevalence"], axis=1)

frame_order = melt_df.drop_duplicates("narrative frame").sort_values("diff_prevalence")["narrative frame"].tolist()
max_val = float(melt_df["prevalence"].max() or 0.0)
x_limit = (max_val * 1.15) if max_val > 0 else 0.05

bar = alt.Chart(melt_df).mark_bar().encode(
    x=alt.X("signed_prev:Q", title="Prevalence (% of relevant articles)", scale=alt.Scale(domain=[-x_limit, x_limit], nice=False), axis=alt.Axis(format=".0%")),
    y=alt.Y("narrative frame:N", sort=frame_order, title="Frame", axis=alt.Axis(labelLimit=0, labelOverlap=False)),
    color=alt.Color("side_key:N", title=None, scale=alt.Scale(domain=["A", "B"], range=["#d7191c", "#2c7bb6"]), legend=alt.Legend(orient="top")),
    tooltip=[
        alt.Tooltip("narrative frame:N", title="Frame"),
        alt.Tooltip("side_key:N", title="Filter"),
        alt.Tooltip("prevalence:Q", title="Prevalence", format=".1%"),
        alt.Tooltip("diff_prevalence:Q", title="(B − A) pp", format=".1%"),
    ],
).properties(
    # title=f"Contrast in Narrative Frames (A: {selected_model_A} vs B: {selected_model_B})",
    # height=max(26 * len(frame_order), 320)
)
st.altair_chart(bar, use_container_width=True)

with st.expander("Raw Contrast Data"):
    st.dataframe(top_contrast[[
        "narrative frame",
        "articles_1", "articles_2",
        "prevalence_1", "prevalence_2",
        "diff_prevalence",
        "abs_diff",
        "support_articles",
    ]])