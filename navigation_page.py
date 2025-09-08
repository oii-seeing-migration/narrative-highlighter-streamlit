import streamlit as st

# ------------------------------------------------------------
# Page config (must be first Streamlit call)
# ------------------------------------------------------------
st.set_page_config(page_title="Narrative Highlighter", layout="wide")

# ------------------------------------------------------------
# Sidebar Navigation (primary)
# ------------------------------------------------------------
st.sidebar.subheader("Navigation")
try:
    st.sidebar.page_link("navigation_page.py", label="Navigation Page", icon="🧭")
    st.sidebar.page_link("pages/01_Narratives_on_Articles.py", label="Narratives on Articles", icon="📰")
    st.sidebar.page_link("pages/02_Aggregative_Dashboard.py", label="Aggregative Dashboard", icon="📊")
    st.sidebar.page_link("pages/03_Contrastive_Dashboard.py", label="Contrastive Dashboard", icon="⚖️")
    st.sidebar.page_link("pages/04_Temporal_Dashboard.py", label="Temporal Dashboard", icon="⏱")
except Exception:
    # Fallback (radio)
    choice = st.sidebar.radio(
        "Go to",
        [
            "Navigation Page",
            "Narratives on Articles",
            "Aggregative Dashboard",
            "Contrastive Dashboard",
            "Temporal Dashboard"
        ],
        key="nav_radio"
    )
    target_map = {
        "Navigation Page": "navigation_page.py",
        "Narratives on Articles": "pages/01_Narratives_on_Articles.py",
        "Aggregative Dashboard": "pages/02_Aggregative_Dashboard.py",
        "Contrastive Dashboard": "pages/03_Contrastive_Dashboard.py",
        "Temporal Dashboard": "pages/04_Temporal_Dashboard.py",
    }
    if choice != "Navigation Page":
        try:
            st.switch_page(target_map[choice])
        except Exception:
            st.sidebar.info("Use built‑in multipage selector at top (deployment limitation).")

# ------------------------------------------------------------
# Helper for body button navigation
# ------------------------------------------------------------
def go(path: str):
    try:
        st.switch_page(path)
    except Exception:
        st.session_state["_nav_fallback"] = True
        st.toast("If navigation failed, use the sidebar links.")

# ------------------------------------------------------------
# Hero Section
# ------------------------------------------------------------
st.markdown("""
# 🧭 Narrative Highlighter

Explore migration-related **narrative frames** and **meso narratives** across news articles.

Use the dashboards below to:
- Inspect per-article narrative fragments
- View aggregate prevalence & intensity
- Contrast frames across two periods
- Track temporal evolution
""")

st.markdown("### Choose a section")

# ------------------------------------------------------------
# BIG BUTTON STYLING
# ------------------------------------------------------------
st.markdown("""
<style>
/* General big button styling */
section.main div.stButton > button {
    width:100%;
    padding:2.1rem 1.4rem;
    font-size:1.20rem;
    font-weight:600;
    border-radius:18px;
    line-height:1.35;
    box-shadow:0 4px 14px rgba(0,0,0,0.18);
    transition:all .15s ease;
    border:0;
    text-align:left;
    white-space:normal;
}
/* Color themes (order-dependent) */
section.main div.stButton:nth-of-type(1) > button {
    background:linear-gradient(135deg,#1f77b4,#4fa3ff);
    color:#fff;
}
section.main div.stButton:nth-of-type(2) > button {
    background:linear-gradient(135deg,#00876c,#4fb783);
    color:#fff;
}
section.main div.stButton:nth-of-type(3) > button {
    background:linear-gradient(135deg,#8b3fa9,#c37bff);
    color:#fff;
}
section.main div.stButton:nth-of-type(4) > button {
    background:linear-gradient(135deg,#b34733,#ff916f);
    color:#fff;
}
section.main div.stButton > button:hover {
    filter:brightness(1.09);
    transform:translateY(-3px);
}
section.main div.stButton > button:active {
    transform:translateY(-1px);
}
@media (max-width: 860px){
  section.main div.stButton > button {
      font-size:1.05rem;
      padding:1.5rem 1.1rem;
  }
}
.desc-blurb {
    margin-top:-0.45rem;
    font-size:0.85rem;
    opacity:0.9;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Button Grid
# ------------------------------------------------------------
c1, c2 = st.columns(2, gap="large")
c3, c4 = st.columns(2, gap="large")

with c1:
    if st.button("📰 Narratives on Articles", key="btn_articles"):
        go("pages/01_Narratives_on_Articles.py")
    st.markdown("<div class='desc-blurb'>Browse articles and view highlighted meso narrative fragments.</div>",
                unsafe_allow_html=True)

with c2:
    if st.button("📊 Aggregative Dashboard", key="btn_agg"):
        go("pages/02_Aggregative_Dashboard.py")
    st.markdown("<div class='desc-blurb'>Rank frames & meso narratives; inspect prevalence, intensity & volume.</div>",
                unsafe_allow_html=True)

with c3:
    if st.button("⚖️ Contrastive Dashboard", key="btn_contrast"):
        go("pages/03_Contrastive_Dashboard.py")
    st.markdown("<div class='desc-blurb'>Compare two time periods; surface frames with largest directional shifts.</div>",
                unsafe_allow_html=True)

with c4:
    if st.button("⏱ Temporal Dashboard", key="btn_time"):
        go("pages/04_Temporal_Dashboard.py")
    st.markdown("<div class='desc-blurb'>Track frame prevalence trends over time (weekly / monthly).</div>",
                unsafe_allow_html=True)

# ------------------------------------------------------------
# Fallback notice
# ------------------------------------------------------------
if st.session_state.get("_nav_fallback"):
    st.info("If buttons did not navigate, use the sidebar links.")

# ------------------------------------------------------------
# Methodology (optional)
# ------------------------------------------------------------
with st.expander("ℹ Methodology Summary"):
    st.markdown("""
**Prevalence** = share of articles containing ≥1 fragment of a frame/meso.  
**Intensity** = avg fragments per article (conditional on presence).  
**Contrast Salience** = standardized prevalence change * log10(support).  
""")

st.markdown("---")
st.caption("© Narrative Highlighter – Analytical Prototype")