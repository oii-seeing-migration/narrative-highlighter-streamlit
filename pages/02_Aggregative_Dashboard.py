# import streamlit as st
# import altair as alt
# import pandas as pd
# from lib.narratives_utils import load_data, aggregate_range

# st.set_page_config(page_title="Aggregative Dashboard", layout="wide")

# st.title("Aggregative Dashboard")

# df = load_data()
# if df["date_dt"].notna().any():
#     dates = df["date_dt"].dropna()
#     min_dt = dates.min().date()
#     max_dt = dates.max().date()
#     st.sidebar.header("Filter")
#     picked = st.sidebar.date_input(
#         "Date range",
#         value=(min_dt, max_dt),
#         min_value=min_dt,
#         max_value=max_dt
#     )
#     if isinstance(picked, tuple) and len(picked) == 2:
#         start_date, end_date = picked
#     else:
#         start_date = end_date = picked
#     mask = (df["date_dt"].dt.date >= start_date) & (df["date_dt"].dt.date <= end_date)
#     df_range = df[mask].copy()
# else:
#     st.info("No valid date column; using full dataset.")
#     df_range = df

# agg = aggregate_range(df_range)
# st.write(f"Articles in range: {agg['total_articles']}")

# # -------------------------------------------------
# # Frames bar chart (ONLY number of articles retained)
# # -------------------------------------------------
# frames = agg["frames_summary"].head(25)
# frames_h = max(24 * len(frames), 360)
# frames_chart = alt.Chart(frames).mark_bar().encode(
#     x=alt.X("articles:Q", title="# Articles"),
#     y=alt.Y(
#         "narrative frame:N",
#         sort="-x",
#         axis=alt.Axis(labelLimit=0, labelOverlap=False),
#         title="Narrative Frame"
#     ),
#     # Single color (remove other encodings since only articles matter)
#     color=alt.value("#1f77b4"),
#     tooltip=[
#         alt.Tooltip("narrative frame:N", title="Frame"),
#         alt.Tooltip("articles:Q", title="# Articles")
#     ],
# ).properties(title="Top Frames (by # Articles)", height=frames_h)
# st.altair_chart(frames_chart, use_container_width=True)

# # -------------------------------------------------
# # Meso narratives: attach dominant parent frame and simplify
# # Label format: Frame: Meso Narrative
# # -------------------------------------------------
# # Use exploded annotations to find dominant (most frequent) frame per meso
# if "exploded" in agg:
#     ex = agg["exploded"]
# else:
#     # Fallback: reconstruct minimal exploded if not returned
#     ex = pd.DataFrame()

# if not ex.empty:
#     meso_parent = (
#         ex[ex["meso narrative"].notna() & (ex["meso narrative"] != "")]
#         .groupby("meso narrative")["narrative frame"]
#         .agg(lambda s: s.value_counts().idxmax() if not s.value_counts().empty else "")
#         .reset_index()
#         .rename(columns={"narrative frame": "parent_frame"})
#     )
#     meso = agg["meso_summary"].merge(meso_parent, on="meso narrative", how="left")
# else:
#     meso = agg["meso_summary"].copy()
#     meso["parent_frame"] = ""

# meso = meso.head(25)
# meso["frame_meso_label"] = meso.apply(
#     lambda r: f"[{r['parent_frame']}]: {r['meso narrative']}" if r["parent_frame"] else r["meso narrative"],
#     axis=1
# )

# meso_h = max(24 * len(meso), 360)
# meso_chart = alt.Chart(meso).mark_bar().encode(
#     x=alt.X("articles:Q", title="# Articles"),
#     y=alt.Y(
#         "frame_meso_label:N",
#         sort="-x",
#         axis=alt.Axis(
#             labelLimit=0,
#             labelOverlap=False,
#             title="Frame: Meso Narrative",
#             titleAngle=270,
#             titlePadding=300,
#             labelPadding=6
#         )
#     ),
#     # Color bars by parent frame to visually separate groups
#     # color=alt.Color("parent_frame:N", title="Frame", legend=alt.Legend(columns=1)),
#     tooltip=[
#         alt.Tooltip("parent_frame:N", title="Frame"),
#         alt.Tooltip("meso narrative:N", title="Meso Narrative"),
#         alt.Tooltip("articles:Q", title="# Articles")
#     ],
# ).properties(title="Top Meso Narratives (by # Articles)", height=meso_h)
# st.altair_chart(meso_chart, use_container_width=True)


# with st.expander("Raw Frame Data"):
#     st.dataframe(agg["frames_summary"][["narrative frame", "articles", "prevalence", "intensity"]])

# with st.expander("Raw Meso Data"):
#     st.dataframe(meso[["parent_frame", "meso narrative", "articles"]])





import os
import streamlit as st
import altair as alt
import pandas as pd
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
load_dotenv()

limit = 200  # Default limit for top N queries
from datetime import datetime, timedelta

st.set_page_config(page_title="Aggregative Dashboard", layout="wide")
st.title("Aggregative Dashboard")

# Config
try:
    DB_URL = st.secrets.get("DATABASE_URL")
except Exception as e:
    DB_URL = os.getenv("DATABASE_URL")



if not DB_URL:
    st.error("DATABASE_URL is not configured. Add it to Streamlit secrets.")
    st.stop()

# Helpers
def connect():
    return psycopg.connect(DB_URL)  # DSN should include sslmode=require

def df_from_query(sql: str, params=()):
    with connect() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("set statement_timeout = '15s'")
        cur.execute("set application_name = 'streamlit_dashboard'")
        cur.execute(sql, params)
        rows = cur.fetchall()
    return pd.DataFrame(rows)

# Helper to normalize domains for cache keys/params
def _normalize_domains(domains):
    if not domains:
        return None
    return tuple(sorted(set(domains)))


# ---------- Queries (RELEVANT only) ----------
@st.cache_data(ttl="7d", show_spinner=True, show_time=True)
def get_date_bounds():
    sql = """
      select
        min(a.pub_date::date) as min_d,
        max(a.pub_date::date) as max_d
      from perigon.articles a
    """
    df = df_from_query(sql)
    if df.empty:
        return None, None
    return df.loc[0, "min_d"], df.loc[0, "max_d"]

@st.cache_data(ttl="7d", show_spinner=True, show_time=True)
def get_available_domains(start_date, end_date):
    sql = """
      select distinct a.source_domain
      from perigon.articles a
      where a.pub_date::date between %s and %s
        and exists (
          select 1
          from perigon.article_summary_annotations x
          where x.article_id = a.article_id
            and x.task in ('frames','meso')
            and jsonb_typeof(x.annotation_parsed)='array'
            and jsonb_array_length(x.annotation_parsed) > 0
        )
      order by 1
    """
    df = df_from_query(sql, (start_date, end_date))
    return df["source_domain"].tolist() if not df.empty else []



@st.cache_data(ttl="7d", show_spinner=True, show_time=True)
def get_total_articles(start_date, end_date, source_domains=None):
    source_domains = _normalize_domains(source_domains)
    sql = """
      select count(distinct a.article_id) as total
      from perigon.articles a
      where a.pub_date::date between %s and %s
        and exists (
          select 1
          from perigon.article_summary_annotations x
          where x.article_id = a.article_id
            and x.task in ('frames','meso')
            and jsonb_typeof(x.annotation_parsed)='array'
            and jsonb_array_length(x.annotation_parsed) > 0
        )
    """
    params = [start_date, end_date]
    if source_domains:
        sql += " and a.source_domain = any(%s)"
        params.append(list(source_domains))
    df = df_from_query(sql, tuple(params))
    return int(df.loc[0, "total"]) if not df.empty else 0

@st.cache_data(ttl="7d", show_spinner=True, show_time=True)
def get_frames_summary(start_date, end_date, limit=limit, source_domains=None):
    source_domains = _normalize_domains(source_domains)
    sql = """
      select
        fr.frame as "narrative frame",
        count(distinct a.article_id) as articles
      from perigon.articles a
      join perigon.article_summary_annotations f
        on f.article_id = a.article_id
       and f.task = 'frames'
       and jsonb_typeof(f.annotation_parsed) = 'array'
       and jsonb_array_length(f.annotation_parsed) > 0
      cross join lateral jsonb_array_elements_text(f.annotation_parsed) as fr(frame)
      where a.pub_date::date between %s and %s
    """
    params = [start_date, end_date]
    if source_domains:
        sql += " and a.source_domain = any(%s)"
        params.append(list(source_domains))
    sql += """
      group by fr.frame
      order by articles desc
      limit %s
    """
    params.append(int(limit))
    return df_from_query(sql, tuple(params))

@st.cache_data(ttl="7d", show_spinner=True, show_time=True)
def get_meso_summary_with_parent(start_date, end_date, limit=limit, source_domains=None):
    source_domains = _normalize_domains(source_domains)
    sql = """
      with expl as (
        select
          a.article_id,
          (e.value->>'meso narrative') as meso_narrative,
          (e.value->>'narrative frame') as narrative_frame
        from perigon.articles a
        join perigon.article_summary_annotations m
          on m.article_id = a.article_id
         and m.task = 'meso'
         and jsonb_typeof(m.annotation_parsed) = 'array'
         and jsonb_array_length(m.annotation_parsed) > 0
        cross join lateral jsonb_array_elements(m.annotation_parsed) as e(value)
        where a.pub_date::date between %s and %s
    """
    params = [start_date, end_date]
    if source_domains:
        sql += " and a.source_domain = any(%s)"
        params.append(list(source_domains))
    sql += """
      ),
      totals as (
        select meso_narrative, count(distinct article_id) as articles
        from expl
        where meso_narrative is not null and meso_narrative <> ''
        group by meso_narrative
      ),
      parent as (
        select
          meso_narrative,
          narrative_frame,
          count(*) as freq,
          row_number() over (partition by meso_narrative order by count(*) desc) as rn
        from expl
        where meso_narrative is not null and meso_narrative <> ''
        group by meso_narrative, narrative_frame
      )
      select
        t.meso_narrative as "meso narrative",
        t.articles,
        coalesce(p.narrative_frame, '') as parent_frame
      from totals t
      left join parent p
        on p.meso_narrative = t.meso_narrative and p.rn = 1
      order by t.articles desc
      limit %s
    """
    params.append(int(limit))
    return df_from_query(sql, tuple(params))


# ---------- UI ----------
min_dt, max_dt = get_date_bounds()
if not min_dt or not max_dt:
    st.info("No annotated articles found.")
    st.stop()

st.sidebar.header("Filter")
picked = st.sidebar.date_input(
    "Date range",
    value=(min_dt, max_dt),
    min_value=min_dt,
    max_value=max_dt,
)
if isinstance(picked, tuple) and len(picked) == 2:
    start_date, end_date = picked
else:
    start_date = end_date = picked

# Source domain filter (defaults to all available in range)
available_domains = get_available_domains(start_date, end_date)
selected_domains = st.sidebar.multiselect(
    "Source domain",
    options=available_domains,
    default=available_domains,
)
domain_filter = _normalize_domains(selected_domains)

total_articles = get_total_articles(start_date, end_date, domain_filter)
st.write(f"Articles in range: {total_articles}")

frames = get_frames_summary(start_date, end_date, limit=limit, source_domains=domain_filter)
st.caption(f"Frames rows: {len(frames)}")
frames_h = max(24 * len(frames), 360) if not frames.empty else 360
frames_chart = alt.Chart(frames).mark_bar().encode(
    x=alt.X("articles:Q", title="# Articles"),
    y=alt.Y("narrative frame:N", sort="-x", axis=alt.Axis(labelLimit=0, labelOverlap=False), title="Narrative Frame"),
    color=alt.value("#1f77b4"),
    tooltip=[alt.Tooltip("narrative frame:N", title="Frame"), alt.Tooltip("articles:Q", title="# Articles")],
).properties(title="Top Frames", height=frames_h)
st.altair_chart(frames_chart, use_container_width=True)

meso = get_meso_summary_with_parent(start_date, end_date, limit=limit, source_domains=domain_filter).copy()
if not meso.empty:
    meso["frame_meso_label"] = meso.apply(
        lambda r: f"[{r['parent_frame']}]: {r['meso narrative']}" if r["parent_frame"] else r["meso narrative"],
        axis=1
    )
st.caption(f"Meso rows: {len(meso)}")
meso_h = max(24 * len(meso), 360) if not meso.empty else 360
meso_chart = alt.Chart(meso).mark_bar().encode(
    x=alt.X("articles:Q", title="# Articles"),
    y=alt.Y(
        "frame_meso_label:N",
        sort="-x",
        axis=alt.Axis(labelLimit=0, labelOverlap=False, title="Frame: Meso Narrative", titleAngle=270, titlePadding=300, labelPadding=6),
    ),
    tooltip=[alt.Tooltip("parent_frame:N", title="Frame"), alt.Tooltip("meso narrative:N", title="Meso Narrative"), alt.Tooltip("articles:Q", title="# Articles")],
).properties(title="Top Meso Narratives", height=meso_h)
st.altair_chart(meso_chart, use_container_width=True)

with st.expander("Raw Frame Data"):
    st.dataframe(frames[["narrative frame", "articles"]])

with st.expander("Raw Meso Data"):
    st.dataframe(meso[["parent_frame", "meso narrative", "articles"]])