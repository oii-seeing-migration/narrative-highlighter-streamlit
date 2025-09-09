# Narrative Highlighter (Guardian)

Streamlit application to explore migration‑related narrative frames and meso narratives in UK news.  
You can (1) read articles with highlighted narrative fragments and (2) view simple dashboards summarising how often frames and meso narratives appear, how they differ across two periods, and how they evolve over time.

## Live App
https://narrative-highlighter-preannotated.streamlit.app/

## Core Concepts
- **Narrative Frame:** Broad thematic lens (e.g., humanitarian, security, economic).
- **Meso Narrative:** More specific motif under a frame, tied to concrete text fragments.
- **Fragment:** Extracted text span illustrating a meso narrative.
- A frame / meso is counted for an article if at least one fragment of it appears.

## Pages

| Page | What You See | Key Controls |
|------|--------------|--------------|
| Navigation Page | Overview + large buttons | Quick jump to any dashboard |
| Narratives on Articles | Article text with highlighted (Frame: Meso) fragments | Filter by frame / meso / date / search |
| Aggregative Dashboard | Top frames and meso narratives by number of articles (selected date range) | Date range picker |
| Contrastive Dashboard | Diverging bar chart comparing frame prevalence between two custom periods | Two date range pickers, min support, top N selector |
| Temporal Dashboard | Weekly / Monthly / Yearly prevalence trends + relative share area plot | Date range, granularity selector, frame multi‑select |

## Metrics Used

| Metric | Meaning |
|--------|---------|
| Articles | Distinct articles containing ≥1 fragment for the frame / meso |
| Prevalence | Articles / Total articles (in the selected range or period) |
| Difference (Contrastive) | Prevalence_B − Prevalence_A (percentage point change) |
| Support (Contrastive) | Articles_A + Articles_B (used to filter out very sparse frames) |

(An internal intensity metric still exists but is not shown on simplified charts.)

## Visualisations

| Chart | Purpose |
|-------|---------|
| Bar (Frames) | Rank frames by article count |
| Bar (Meso) | Rank meso narratives; label shows parent frame (e.g., [Frame]: Meso) |
| Diverging Bar (Contrast) | Left = Period A prevalence, Right = Period B prevalence; ordered by difference |
| Temporal Line | Prevalence trajectory over time (weekly / monthly / yearly) |
| Temporal Stacked Area | Relative share of selected frames within each period |
| Highlighted Article View | Inline color spans: Frame (Meso) fragment text |

## Data Input

Place the annotated corpus in `data/GuardianCorpus_Vahid_AI_Annotated.csv` with at least:
- `title`
- `body`
- `date` (ISO 8601; UTC recommended)
- `classification_Meso_Qwen3-32B` (stringified dict with a `results` list)
- (Optional) `classification_FrameU_Qwen3-32B` if frame list strings are needed elsewhere

Meso annotation format per article (parsed):
```json
{
  "results": [
    {
      "narrative frame": "Security",
      "meso narrative": "Border enforcement pressure",
      "text fragment": "…exact text…"
    }
  ]
}
```

## Processing (Simplified Pipeline)

1. Load CSV & parse dates (UTC).
2. Convert meso annotation strings to dicts.
3. Explode to one row per fragment.
4. Canonicalise labels (Unicode + whitespace cleanup).
5. Aggregate:
   - Frames: article counts and prevalence.
   - Meso: article counts (+ attach dominant parent frame).
6. Contrast:
   - Compute prevalence in Period A and Period B.
   - Filter by minimum combined article support.
   - Sort by absolute prevalence difference.
7. Temporal:
   - Resample to weekly / monthly / yearly buckets.
   - Compute per‑frame prevalence per period.

## Architecture

```
narrative-highlighter-streamlit/
├─ navigation_page.py
├─ pages/
│  ├─ 01_Narratives_on_Articles.py
│  ├─ 02_Aggregative_Dashboard.py
│  ├─ 03_Contrastive_Dashboard.py
│  ├─ 04_Temporal_Dashboard.py
├─ lib/
│  ├─ __init__.py
│  └─ narratives_utils.py
└─ data/
```

`lib/narratives_utils.py` provides:
- `load_data`
- `explode_mesos`
- `aggregate_range`
- `compute_frame_contrast`
- `time_series_frames`

## Design Simplifications

| Goal | Choice |
|------|--------|
| Fast interpretation | Show only article counts prominently |
| Clear period comparison | Diverging bar instead of abstract salience score |
| Reduce clutter | Removed fragment count bars & advanced scatter |
| Label clarity | Multi-line / framed meso labels, dynamic chart height |
| Robust grouping | Canonical normalization of text labels |
| Performance | `st.cache_data` for loading & derived aggregates |

## Possible Extensions

- Re‑introduce intensity & fragments as optional toggles.
- Meso-level contrast view.
- Frame co‑occurrence network.
- Download (CSV / image) exports.
- Manual vs model annotation comparison.

## License
MIT

© Narrative Highlighter – Research & Analytical