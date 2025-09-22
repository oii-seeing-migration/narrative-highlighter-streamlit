import os
from datetime import date
import streamlit as st
import pandas as pd
from psycopg import connect
from psycopg.rows import dict_row
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt

st.title("🧩 Wordclouds from Summaries")

def get_db_url() -> str:
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        from dotenv import load_dotenv
        load_dotenv()
        return os.getenv("DATABASE_URL")

DB_URL = get_db_url()
if not DB_URL:
    st.error("DATABASE_URL not configured. Add it to Streamlit Secrets or .env.")
    st.stop()

@st.cache_data(show_spinner=False, ttl=300)
def fetch_meta():
    with connect(DB_URL) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select min(pub_date::date) as min_d, max(pub_date::date) as max_d from perigon.articles where summary is not null and summary <> ''")
            r = cur.fetchone() or {}
            cur.execute("select distinct source_domain from perigon.articles where source_domain is not null order by 1")
            domains = [x["source_domain"] for x in cur.fetchall()]
    return (r.get("min_d"), r.get("max_d")), domains

@st.cache_data(show_spinner=True, ttl=300)
def fetch_rows(d0: date, d1: date, domains: list[str] | None, limit: int = 5000) -> pd.DataFrame:
    sql = """
        select article_id, source_domain, pub_date, summary
        from perigon.articles
        where summary is not null and summary <> ''
          and pub_date::date between %s and %s
    """
    params = [d0, d1]
    if domains:
        sql += " and source_domain = any(%s)"
        params.append(domains)
    sql += " order by pub_date desc limit %s"
    params.append(limit)
    with connect(DB_URL) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["article_id","source_domain","pub_date","summary"])
    if not df.empty:
        df["pub_date"] = pd.to_datetime(df["pub_date"], utc=True, errors="coerce")
    return df

# Sidebar filters
date_range, all_domains = fetch_meta()
if not date_range[0] or not date_range[1]:
    st.info("No data available yet.")
    st.stop()

st.sidebar.header("Filter")
picked = st.sidebar.date_input(
    "Date range",
    value=(date_range[0], date_range[1]),
    min_value=date_range[0],
    max_value=date_range[1]
)
if isinstance(picked, tuple) and len(picked) == 2:
    start_date, end_date = picked
else:
    start_date = end_date = picked

domains_selected = st.sidebar.multiselect(
    "Source domains",
    options=all_domains,
    default=all_domains
)
limit = st.sidebar.slider("Max rows to load", 500, 20000, 5000, step=500)

df = fetch_rows(start_date, end_date, domains_selected if domains_selected and len(domains_selected) < len(all_domains) else None, limit)

st.write(f"Articles in range: {len(df):,}")

if df.empty:
    st.warning("No summaries for the selected filters.")
    st.stop()

# Build wordcloud text
text = " ".join([t for t in df["summary"].dropna().astype(str).tolist() if t.strip()])
if not text:
    st.warning("No non-empty summaries found.")
    st.stop()

custom_stop = {
    "said","says","say","will","one","us","uk","bbc","guardian","telegraph",
    "migrant","migrants","asylum","refugee","refugees"  # optionally filter core terms
}
wc = WordCloud(
    width=1200, height=600, background_color="white",
    stopwords=STOPWORDS.union(custom_stop),
    collocations=True
).generate(text)

fig, ax = plt.subplots(figsize=(12,6))
ax.imshow(wc, interpolation="bilinear")
ax.axis("off")
st.pyplot(fig, use_container_width=True)

with st.expander("Preview rows"):
    st.dataframe(df[["pub_date","source_domain","summary"]].head(100))
