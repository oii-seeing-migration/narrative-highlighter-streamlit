# Narrative Highlighter (Guardian)

Interactive multi‑page Streamlit application for exploring migration‑related narratives in UK news.  
It surfaces how macro (frame) and meso narratives appear, shift, co‑occur, and evolve over time — and lets you drill down to the exact text fragments in articles.

## Live App

https://narrative-highlighter-preannotated.streamlit.app/

## Core Concepts

- **Narrative Frame (macro):** Broad interpretive lens (e.g., humanitarian, security, economic).
- **Meso Narrative:** More specific narrative motif nested under a frame; linked to concrete article fragments.
- **Text Fragment:** Extracted span illustrating the meso narrative.
- **Article-Level Presence:** A frame/meso “occurs” in an article if ≥1 fragment is annotated.

## Functional Pages

| Page | Purpose | Key Interactions |
|------|---------|------------------|
| Navigation Page | Project introduction & quick access | Large action buttons + sidebar links |
| Narratives on Articles | Article-level exploration with highlighting | Filter by frame / meso / title; fragment highlighting with tooltips |
| Aggregative Dashboard | Whole‑range ranking & distribution | Top frames & meso narratives; prevalence vs intensity scatter |
| Contrastive Dashboard | Compare two custom time periods | Salience ranking (directional shifts); prevalence slope (A→B) |
| Temporal Dashboard | Longitudinal dynamics | Weekly / monthly prevalence lines & relative share (stacked area) |

## Metrics

| Metric | Level | Definition |
|--------|-------|------------|
| Articles | Frame / Meso | Number of distinct articles containing ≥1 fragment |
| Fragments | Frame / Meso | Total annotated fragments |
| Prevalence | Frame / Meso | Articles / Total Articles in selected range |
| Intensity | Frame / Meso | Fragments per article (conditional on presence) |
| Salience (Contrastive) | Frame | Standardized prevalence difference * log10(combined support) |
| Support Articles | Frame | Articles_A + Articles_B (contrast periods) |

**Salience rationale:** Balances effect size (standardized difference) with reliability (log-scaled support) so extremely sparse narratives do not dominate.

## Visual Components

- **Ranked Bar Charts:** Top frames and meso narratives (article counts; color encodes prevalence / size).
- **Scatter (Frames):** Prevalence (x) vs intensity (y) with point size = volume.
- **Contrast Bars:** Directional salience (blue = higher in Period B, red = higher in Period A).
- **Prevalence Slope Plot:** Two-period comparison (A vs B).
- **Temporal Line Chart:** Prevalence trajectories by frame.
- **Stacked Area (Temporal):** Relative share composition among selected frames.
- **Highlighted Article View:** Inline fragment spans with (Frame: Meso) tooltip.

## Data Requirements

Place under `data/`:

| File | Purpose | Required Columns |
|------|---------|------------------|
| `GuardianCorpus_Vahid_AI_Annotated.csv` | Core annotated corpus | `title`, `body`, `date` (ISO8601, e.g. `2025-07-27T18:22:16Z`), `classification_FrameU_Qwen3-32B`, `classification_Meso_Qwen3-32B` |
| `frame_meso_counts.xlsx` | (Optional) Supplemental counts | `narrative frame`, `meso narrative`, `count` |
| `all_frames_counts.xlsx` | (Optional) Frame frequency | `narrative frame`, `count` |

`classification_Meso_Qwen3-32B` must parse to a dict:
```json
{
  "results": [
    {
      "narrative frame": "…",
      "meso narrative": "…",
      "text fragment": "…"
    }
  ]
}
```

## Processing Pipeline

1. **Load & Parse:** CSV read; date parsed to UTC; meso JSON-like strings → dict.
2. **Explode Annotations:** One row per (article, fragment).
3. **Canonicalize Text Labels:** Unicode normalization, whitespace collapse (prevents duplicate bins).
4. **Aggregate:**
   - Frames: distinct article count, fragment count, prevalence, intensity.
   - Meso: same metrics overall (optionally extendable per frame).
5. **Contrast (Two Ranges):**
   - Compute prevalence in Period A & B.
   - Standardize difference using pooled variance.
   - Weight by log10 support → salience.
6. **Temporal Aggregation:** Resample by period (weekly / monthly) → prevalence time series.
7. **Visualization:** Altair charts rendered with responsive layout and label preservation.

## Architecture & Code Layout

```
narrative-highlighter-streamlit/
├─ navigation_page.py                 # Landing page
├─ pages/
│  ├─ 01_Narratives_on_Articles.py    # Article-level exploration
│  ├─ 02_Aggregative_Dashboard.py     # Aggregated metrics
│  ├─ 03_Contrastive_Dashboard.py     # Two-period contrast
│  ├─ 04_Temporal_Dashboard.py        # Time series analysis
├─ lib/
│  ├─ __init__.py
│  └─ narratives_utils.py             # Shared data logic & metrics
├─ data/                              # Input corpus + auxiliary files
└─ README.md
```

`lib/narratives_utils.py` exposes:
- `load_data`
- `explode_mesos`
- `aggregate_range`
- `compute_frame_contrast`
- `time_series_frames`

## Caching & Performance

- `st.cache_data` wraps loading + heavy aggregations to reduce recomputation.
- Canonicalization minimizes categorical explosion.
- Contrast & temporal computations operate on filtered subsets to stay responsive.
- Log-scaling in salience mitigates noise from rare frames.

## Design Choices

| Concern | Approach |
|---------|----------|
| Duplicate Labels | Canonical normalization (Unicode NFKC, whitespace collapse) |
| Overplot / Long Labels | Dynamic chart height (≈24px per category), `labelLimit=0`, disabled overlap |
| Sparse Noise in Contrast | Salience weighting with log support + min support threshold |
| User Flexibility | Independent date pickers per period; multi-select frames in temporal page |
| Extensibility | Shared utility module; pages are thin composition layers |
| Reproducibility | Deterministic grouping; explicit article IDs |

## Extensibility Ideas

- Meso-level contrast (analogous to frame contrast).
- Co-occurrence network visualization (force layout, thresholded edges).
- Narrative clustering via semantic embeddings of fragments.
- Export panel: CSV / PNG downloads of current charts.
- Incremental annotation comparison (manual vs automated).
- Quality diagnostics: fragment length distributions, redundancy ratios.

## Limitations

- Assumes annotation schema consistency (exact key names in meso dict).
- Does not deduplicate overlapping fragments.
- Salience assumes independent article samples (no weighting for article length).
- Time zone normalization relies on ISO UTC inputs.

## License

MIT

© Narrative Highlighter – Research & Analytical