import pandas as pd
import json
import re
import streamlit as st
import ast

# -----------------------------
# Load data
# -----------------------------
st.set_page_config(page_title="Narrative Highlighter", layout="wide")

@st.cache_data(show_spinner=True)
def load_data():
    data_file_name = "GuardianCorpus_Vahid"
    data_df = pd.read_csv(f"data/{data_file_name}_AI_Annotated.csv")
    frame_meso_df = pd.read_excel("data/frame_meso_counts.xlsx")
    frames_df = pd.read_excel("data/all_frames_counts.xlsx")

    data_df.dropna(subset=['classification_Meso_Qwen3-32B'], inplace=True)

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

    data_df['classification_Meso_Qwen3-32B'] = data_df['classification_Meso_Qwen3-32B'].apply(_parse_mesos)
    return data_df, frame_meso_df, frames_df


# -----------------------------
# Streamlit config
# -----------------------------
st.set_page_config(page_title="Narrative Highlighter", layout="wide")

# -----------------------------
# Sidebar navigation
# -----------------------------
st.sidebar.subheader("Navigation")
try:
    st.sidebar.page_link("navigation_page.py", label="Navigation Page", icon="🧭")
    st.sidebar.page_link("pages/01_Narratives_Dashboard.py", label="Narratives Dashboard", icon="📊")
    st.sidebar.page_link("pages/02_Narratives_on_Articles.py", label="Narratives on Articles", icon="📰")
except Exception:
    nav_choice = st.sidebar.radio(
        "Go to",
        ["Navigation Page", "Narratives Dashboard", "Narratives on Articles"],
        key="nav_radio"
    )
    target_map = {
        "Navigation Page": "navigation_page.py",
        "Narratives Dashboard": "pages/01_Narratives_Dashboard.py",
        "Narratives on Articles": "pages/02_Narratives_on_Articles.py",
    }
    if target_map[nav_choice].endswith(".py"):
        try:
            st.switch_page(target_map[nav_choice])
        except Exception:
            st.sidebar.info("Use the built-in page selector (Streamlit multipage menu) to navigate.")

# Load (spinner will appear now)
data_df, frame_meso_df, frames_df = load_data()

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Filters")

# Clear filters button
if st.sidebar.button("Clear filters"):
    st.session_state['frame_sel'] = "(All)"
    st.session_state['meso_sel'] = "(All)"

# 1) Narrative frame
frame_options = sorted(frames_df['narrative frame'].dropna().unique().tolist())
frame_sel = st.sidebar.selectbox(
    "Narrative Frame",
    ["(All)"] + frame_options,
    index=0,
    key="frame_sel"
)

# 2) Meso narrative (dependent on frame)
if st.session_state.get('frame_sel', "(All)") != "(All)":
    meso_options = (
        frame_meso_df[frame_meso_df['narrative frame'] == frame_sel]['meso narrative']
        .dropna().unique().tolist()
    )
    meso_sel = st.sidebar.selectbox(
        "Meso Narrative",
        ["(All)"] + sorted(meso_options),
        index=0,
        key="meso_sel"
    )
else:
    meso_sel = st.sidebar.selectbox(
        "Meso Narrative",
        ["(All)"],
        index=0,
        key="meso_sel"
    )

# -----------------------------
# Filter articles based on selections
# -----------------------------
filtered_df = data_df

def _has_frame_and_meso(row_frame_meso_dict, frame_val, meso_val):
    results = row_frame_meso_dict.get("results", []) if isinstance(row_frame_meso_dict, dict) else []
    return any(
        (str(r.get('narrative frame')) == frame_val) and (str(r.get('meso narrative')) == meso_val)
        for r in results if isinstance(r, dict)
    )

if frame_sel != "(All)" and meso_sel != "(All)":
    filtered_df = data_df[
        data_df['classification_Meso_Qwen3-32B'].apply(
            lambda d: _has_frame_and_meso(d, frame_sel, meso_sel)
        )
    ]
elif frame_sel != "(All)":
    # Only frame selected: use comma-separated frames column to filter
    def _row_has_frame(val, target):
        frames = [f.strip() for f in str(val or "").split(",")]
        return any(f.lower() == target.lower() for f in frames if f)
    filtered_df = data_df[data_df['classification_FrameU_Qwen3-32B'].apply(lambda v: _row_has_frame(v, frame_sel))]

# 3) Article title selector (based on filtered set)
article_titles = filtered_df['title'].tolist()
if not article_titles:
    st.sidebar.warning("No matching articles.")
    st.stop()

selected_title = st.sidebar.selectbox("Select Article", article_titles)
article = filtered_df[filtered_df['title'] == selected_title].iloc[0]

# -----------------------------
# Page content
# -----------------------------
st.title(article['title'])
if 'webUrl' in article:
    st.markdown(f"[Read full article here]({article['webUrl']})", unsafe_allow_html=True)

# Parse labels from already-parsed dict
parsed_dict = article['classification_Meso_Qwen3-32B']
labels = parsed_dict.get("results", [])
article_body = article['body']

# Sort fragments by length to avoid nested replacements
labels_sorted = sorted(labels, key=lambda x: len(x.get('text fragment', '')), reverse=True)

def highlight_text(text, narrative_frame, meso_narrative):
    tooltip = f"{narrative_frame}: {meso_narrative}"
    return f"""<span class="highlight" title="{tooltip}">{text}</span>"""

for label in labels_sorted:
    frag_text = label.get('text fragment')
    if not frag_text:
        continue
    frag = re.escape(frag_text)
    replacement = highlight_text(
        frag_text,
        label.get('narrative frame', ''),
        label.get('meso narrative', '')
    )
    article_body = re.sub(frag, replacement, article_body, count=1)

# -----------------------------
# CSS for hover effect
# -----------------------------
st.markdown("""
<style>
.highlight {
    background-color: #fffd75;
    cursor: help;
    border-radius: 3px;
    padding: 2px;
}
.highlight:hover {
    background-color: #ffeb3b;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Display article with highlights
# -----------------------------
st.markdown(article_body, unsafe_allow_html=True)