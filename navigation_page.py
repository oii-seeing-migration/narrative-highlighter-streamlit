import streamlit as st

# -------------------------------------------------------------------
# Page config (must be first Streamlit call)
# -------------------------------------------------------------------
st.set_page_config(page_title="Narrative Highlighter", layout="wide")

# -------------------------------------------------------------------
# Helper for safe navigation from body buttons
# -------------------------------------------------------------------
def go(path: str):
    try:
        st.switch_page(path)
    except Exception:
        st.session_state["_nav_fallback"] = True
        st.toast("If navigation failed, use the sidebar links.")

# Intro
st.markdown("""
# 🧭 Narrative Highlighter
Explore migration-related narrative frames and meso narratives.
""")

st.markdown("### Choose a section")

# BIG BUTTON STYLING (applies only to buttons rendered below)
st.markdown("""
<style>
/* Scope to main container so we don’t affect sidebar buttons */
section.main div.stButton > button {
    width:100%;
    padding:2.4rem 1.6rem;
    font-size:1.35rem;
    font-weight:600;
    border-radius:18px;
    line-height:1.35;
    box-shadow:0 4px 14px rgba(0,0,0,0.18);
    transition:all .15s ease;
    border:0;
}
/* First button (Dashboard) gradient */
div.stButton:nth-of-type(1) > button {
    background:linear-gradient(135deg,#1f77b4,#4fa3ff);
    color:#fff;
}
/* Second button (Articles) gradient */
div.stButton:nth-of-type(2) > button {
    background:linear-gradient(135deg,#6a3fb6,#a078ff);
    color:#fff;
}
section.main div.stButton > button:hover {
    filter:brightness(1.08);
    transform:translateY(-2px);
}
section.main div.stButton > button:active {
    transform:translateY(0);
}
@media (max-width: 820px){
  section.main div.stButton > button {
      padding:1.6rem 1.2rem;
      font-size:1.15rem;
  }
}
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    if st.button("📊 Narratives Dashboard", key="dash_btn"):
        go("pages/01_Narratives_Dashboard.py")
    st.markdown(
        "<div style='margin-top:-0.4rem; font-size:0.9rem;'>Aggregate metrics: prevalence, intensity, rankings, co-occurrence.</div>",
        unsafe_allow_html=True
    )

with col2:
    if st.button("📰 Narratives on Articles", key="articles_btn"):
        go("pages/02_Narratives_on_Articles.py")
    st.markdown(
        "<div style='margin-top:-0.4rem; font-size:0.9rem;'>Inspect individual articles with highlighted meso narrative fragments.</div>",
        unsafe_allow_html=True
    )

if st.session_state.get("_nav_fallback"):
    st.info("If buttons did not navigate, use the sidebar links.")

st.markdown("---")
st.caption("© Narrative Highlighter – Research / Analytical Prototype")