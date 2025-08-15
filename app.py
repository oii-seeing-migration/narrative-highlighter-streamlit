# %%
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
import json
import re
import os
import random
import numpy as np
from tqdm.notebook import tqdm
tqdm.pandas()

import streamlit as st


# %%
import csv
data_file_name = f'GuardianCorpus_Vahid'

data_df = pd.read_csv(f"/data/vahid.ghafouri/Meso/{data_file_name}_AI_Annotated.csv")
data_df.head(1)
data_df.dropna(subset=['classification_Meso_Qwen3-32B'], inplace=True)

# %%
print(data_df['classification_Meso_Qwen3-32B'][0])

# %%
import ast
ast.literal_eval(data_df['classification_Meso_Qwen3-32B'][0])
# json.loads(data_df['classification_Meso_Qwen3-32B'][0])

# %%
st.set_page_config(page_title="Narrative Highlighter", layout="wide")

# -----------------------------
# Sidebar: Choose Article
# -----------------------------
article_titles = data_df['title'].tolist()
selected_title = st.sidebar.selectbox("Select Article", article_titles)
article = data_df[data_df['title'] == selected_title].iloc[0]

st.title(article['title'])
st.markdown(f"[Read full article here]({article['webUrl']})", unsafe_allow_html=True)

# -----------------------------
# Parse json_label using ast.literal_eval
# -----------------------------
parsed_dict = ast.literal_eval(article['classification_Meso_Qwen3-32B'])
labels = parsed_dict.get("results", [])
article_body = article['body']

# Sort fragments by length to avoid nested replacements
labels_sorted = sorted(labels, key=lambda x: len(x['text fragment']), reverse=True)

def highlight_text(text, narrative_frame, meso_narrative):
    tooltip = f"{narrative_frame}: {meso_narrative}"
    return f"""<span class="highlight" title="{tooltip}">{text}</span>"""

for label in labels_sorted:
    frag = re.escape(label['text fragment'])
    replacement = highlight_text(label['text fragment'],
                                  label['narrative frame'],
                                  label['meso narrative'])
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


