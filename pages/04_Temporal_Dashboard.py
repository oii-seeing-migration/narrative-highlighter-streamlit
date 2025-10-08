import os
import streamlit as st
import altair as alt
import pandas as pd
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()
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

# -------------------------------
# DB config and helpers
# -------------------------------
try:
    DB_URL = st.secrets.get("DATABASE_URL")
except Exception:
    DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    st.error("DATABASE_URL is not configured. Set it in .env or Streamlit secrets.")
    st.stop()

def connect():
    return psycopg.connect(DB_URL)

def df_from_query(sql: str, params=()):
    with connect() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("set statement_timeout = '15s'")
        cur.execute("set application_name = 'temporal_dashboard'")
        cur.execute(sql, params)
        rows = cur.fetchall()
    return pd.DataFrame(rows)

def _normalize_domains(domains):
    if not domains:
        return None
    return tuple(sorted(set(domains)))

# Add: axis/scale helper for time ticks
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

# -------------------------------
# Cached queries
# -------------------------------
@st.cache_data(ttl="7d", show_spinner=True)
def get_date_bounds():
    sql = """
      select
        min(a.pub_date::date) as min_d,
        max(a.pub_date::date) as max_d
      from perigon.articles a
      where exists (
        select 1
        from perigon.article_summary_annotations f
        where f.article_id = a.article_id
          and f.task = 'frames'
          and jsonb_typeof(f.annotation_parsed)='array'
          and jsonb_array_length(f.annotation_parsed) > 0
      )
    """
    df = df_from_query(sql)
    if df.empty:
        return None, None
    return df.loc[0, "min_d"], df.loc[0, "max_d"]

@st.cache_data(ttl="7d", show_spinner=True)
def get_available_domains(start_date, end_date):
    sql = """
      select distinct a.source_domain
      from perigon.articles a
      where a.pub_date::date between %s and %s
        and exists (
          select 1
          from perigon.article_summary_annotations f
          where f.article_id = a.article_id
            and f.task = 'frames'
            and jsonb_typeof(f.annotation_parsed)='array'
            and jsonb_array_length(f.annotation_parsed) > 0
        )
      order by 1
    """
    df = df_from_query(sql, (start_date, end_date))
    return df["source_domain"].tolist() if not df.empty else []

@st.cache_data(ttl="7d", show_spinner=True)
def get_frames_time_series(start_date, end_date, freq_unit: str, source_domains=None):
    """
    freq_unit: one of ('week','month','year') mapped from UI.
    Returns: period (date), narrative frame, articles, prevalence
    """
    # Sanitize freq_unit to allowed tokens to avoid SQL injection
    freq_unit = {"Weekly": "week", "Monthly": "month", "Yearly": "year"}[freq_unit]

    domains = _normalize_domains(source_domains)
    params = [start_date, end_date]

    # Dynamic domain filter
    domain_where = ""
    if domains:
        domain_where = " and b.source_domain = any(%s) "
        params.append(list(domains))

    sql = f"""
      with base as (
        select a.article_id, a.pub_date, a.source_domain
        from perigon.articles a
        where a.pub_date::date between %s and %s
      ),
      frames_exploded as (
        select
          date_trunc('{freq_unit}', b.pub_date)::date as period,
          b.article_id,
          fr.frame
        from base b
        join perigon.article_summary_annotations f
          on f.article_id = b.article_id
         and f.task = 'frames'
         and jsonb_typeof(f.annotation_parsed)='array'
         and jsonb_array_length(f.annotation_parsed) > 0
        cross join lateral jsonb_array_elements_text(f.annotation_parsed) as fr(frame)
        where true
        {domain_where}
      ),
      totals as (
        select period, count(distinct article_id) as total
        from frames_exploded
        group by period
      )
      select
        fe.period,
        fe.frame as "narrative frame",
        count(distinct fe.article_id) as articles,
        (count(distinct fe.article_id)::float / t.total) as prevalence
      from frames_exploded fe
      join totals t on t.period = fe.period
      group by fe.period, fe.frame, t.total
      order by fe.period, articles desc
    """
    df = df_from_query(sql, tuple(params))
    if not df.empty:
        df["period"] = pd.to_datetime(df["period"])
    return df

# -------------------------------
# UI controls
# -------------------------------
min_dt, max_dt = get_date_bounds()
if not min_dt or not max_dt:
    st.error("No frame-annotated articles found.")
    st.stop()

st.sidebar.header("Temporal Settings")
freq = st.sidebar.selectbox("Granularity", ["Weekly", "Monthly", "Yearly"], index=0)

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

# Domain filter
available_domains = get_available_domains(start_date, end_date)
selected_domains = st.sidebar.multiselect(
    "Source domain",
    options=available_domains,
    default=available_domains,
)

# -------------------------------
# Load time series
# -------------------------------
ts = get_frames_time_series(start_date, end_date, freq, selected_domains)
if ts.empty:
    st.info("No data in selected range.")
    st.stop()

# Top frames overall to help select
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

# -------------------------------
# Charts
# -------------------------------
axis_x, scale_x = _time_axis_and_scale(freq)

line = alt.Chart(plot_df).mark_line(point=True).encode(
    x=alt.X("period:T", axis=axis_x, scale=scale_x),
    y=alt.Y("prevalence:Q", axis=alt.Axis(format=".0%"), title="Prevalence"),
    color=alt.Color("narrative frame:N", title="Frame"),
    tooltip=[
        alt.Tooltip("narrative frame:N", title="Frame"),
        alt.Tooltip("period:T", title="Period"),
        alt.Tooltip("articles:Q", title="# Articles"),
        alt.Tooltip("prevalence:Q", format=".1%", title="Prevalence"),
    ]
).properties(title=f"Frame Prevalence Over Time ({freq})")
st.altair_chart(line, use_container_width=True)

area = alt.Chart(plot_df).mark_area(interpolate="monotone").encode(
    x=alt.X("period:T", axis=axis_x, scale=scale_x),
    y=alt.Y("prevalence:Q", stack="normalize", axis=alt.Axis(format=".0%"), title="Share (selected frames)"),
    color=alt.Color("narrative frame:N", title="Frame"),
    tooltip=[
        alt.Tooltip("narrative frame:N", title="Frame"),
        alt.Tooltip("period:T", title="Period"),
        alt.Tooltip("prevalence:Q", format=".1%", title="Prevalence"),
    ]
).properties(title="Relative Share (Selected Frames)")
st.altair_chart(area, use_container_width=True)

with st.expander("Underlying Time Series Data"):
    st.dataframe(plot_df.sort_values(["period", "narrative frame"]))