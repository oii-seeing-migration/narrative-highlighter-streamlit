# Narrative Highlighter (Guardian)

Interactive Streamlit app to explore migration-related narratives in UK news articles annotated with:
- Narrative frames (macro)
- Meso narratives (children) with text fragments

The app highlights text fragments for selected meso narratives and lets you filter articles by frame and meso.

## Streamlit URL

For usage, simply open the app from here:
https://narrative-highlighter-preannotated.streamlit.app/

## Features

- Sidebar filters:
  1) Narrative Frame
  2) Meso Narrative (auto-filtered by selected frame)
  3) Article Title (auto-filtered by frame/meso)
- Clear filters button
- In-text highlighting with hover tooltip “Frame: Meso”

## Data inputs

Place these files under `data/`:

- `GuardianCorpus_Vahid_AI_Annotated.csv`
  - Required columns:
    - `title` (str)
    - `body` (str, HTML-safe)
    - `webUrl` (str, optional)
    - `classification_FrameU_Qwen3-32B` (str: comma-separated frames)
    - `classification_Meso_Qwen3-32B` (JSON or JSON-like str parsable to dict):
      ```
      {
        "results": [
          {
            "narrative frame": "...",
            "meso narrative": "...",
            "text fragment": "..."
          },
          ...
        ]
      }
      ```
- `frame_meso_counts.xlsx` (columns: `narrative frame`, `meso narrative`, `count`)
- `all_frames_counts.xlsx` (columns: `narrative frame`, `count`)

Tip: You can generate these from the notebook in `Meso_Narratives/Group-Narratives.ipynb`.

## Quick start

```bash
# 1) Clone and enter
git clone https://github.com/YOUR_USER/narrative-highlighter-streamlit.git
cd narrative-highlighter-streamlit

# 2) Create venv (Ubuntu)
python3 -m venv .venv
source .venv/bin/activate

# 3) Install deps
pip install --upgrade pip
pip install -r requirements.txt || pip install streamlit pandas openpyxl

# 4) Run
streamlit run app.py
# Open: http://localhost:8501
```

Run on a remote server:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
# Then visit: http://YOUR_SERVER_IP:8501
```

## Usage

- Choose a Narrative Frame to filter both the Meso selector and article list.
- Optionally choose a Meso Narrative to further narrow the article list.
- If neither is selected (“(All)”), all articles are listed.
- Click “Clear filters” to reset.
- Selected article displays with highlighted text fragments (hover for tooltip).

## Troubleshooting

- No articles with frame-only filter:
  - Ensure `classification_FrameU_Qwen3-32B` is cleaned of prefixes like “Frame1:”. The app normalizes them, but mismatches in data formatting can still cause empty results.
- Meso not found:
  - Ensure `classification_Meso_Qwen3-32B` parses to a dict with key `results` and items holding `narrative frame`, `meso narrative`, and `text fragment`.
- Excel read errors:
  - Install `openpyxl` (used by pandas to read `.xlsx`): `pip install openpyxl`.

## Project structure

```
narrative-highlighter-streamlit/
├─ app.py
├─ data/
│  ├─ GuardianCorpus_Vahid_AI_Annotated.csv
│  ├─ frame_meso_counts.xlsx
│  └─ all_frames_counts.xlsx
└─ README.md
```

## License

MIT