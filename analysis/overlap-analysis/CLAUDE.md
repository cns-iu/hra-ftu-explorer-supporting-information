# CLAUDE.md

Guidance for working in `analysis/overlap-analysis/`. The repo-wide overview is in the root `CLAUDE.md`.

## What this is

A small numbered pipeline that compares the cell types (unique CL IDs) in the 2D FTU illustrations with the ones the four CTann annotation-tool crosswalks (Azimuth, CellTypist, popV and FR-Match) map to. Its layout copies `analysis/oral-cavity-data-analysis/`.

```bash
cd analysis/overlap-analysis
python run-all.py   # runs scripts/00-setup_env.py (creates scripts/.venv, installs scripts/requirements.txt), then every other scripts/*.py in filename order
```

- To run one stage on its own: `cd scripts && .venv/bin/python 20-upset-cl-id-overlap.py`. Scripts assume `cwd` is `scripts/`, because `run-all.py` sets it there.
- `run-all.py` skips `shared.py` and `00-setup_env.py`, and stops at the first script that fails.
- A new stage only needs a numeric prefix. That prefix decides when it runs.

## Layout

- `config.yaml`: the inputs for this analysis. Each entry under `downloads:` has `label`, `url`, `accept` (the HTTP Accept header), `format` (which reader pulls CL IDs from the file) and `filename`. Add new inputs here, not as literals in a script. This file is separate from the repo-root `config.yaml` so the analysis stays self-contained.
- `scripts/shared.py`: adds the repo root to `sys.path` and does `from shared_common import *`, which brings in the root `config`. It loads this folder's config as `OVERLAP_CONFIG`/`DOWNLOADS`; that name is deliberately not `config`, so it doesn't shadow the root one. It also defines `OVERLAP_DIR`, `RAW_DATA_DIR` (gitignored) and `REPORTS_DIR`, creates the two folders, and provides `download_path(key)`, which gives the local path of a download.
- `scripts/10-download-files.py`: downloads every `downloads` entry into `raw-data/` with its Accept header. A file that already exists is skipped (delete it to fetch it again). Each file is written to `*.part` first and renamed when complete.
- `scripts/20-upset-cl-id-overlap.py`: builds an UpSet plot of unique CL IDs across all downloaded files and writes three files to `reports/`:
  - `upset-cl-id-overlap.png`, saved at 600 dpi
  - `cl-id-overlap-intersections.csv`, one row per combination of files with its count
  - `cl-id-overlap-memberships.csv`, one row per CL ID with a True/False column per file

## Input formats (verified 2026-11-16)

- **2D FTU crosswalk** (`format: ftu-crosswalk-csv`, pinned to v1.6 on cdn.humanatlas.io):
  - It has 11 metadata lines (title, authors, DOI, date and so on) before the header row, so read it with `pd.read_csv(..., skiprows=11)`.
  - The `OntologyID` column mixes CL IDs (cell types) with UBERON IDs (anatomical-structure nodes) and NaN. Keep only values that start with `CL:`.
  - `representation_of` holds the same ID as an OBO PURL (`http://purl.obolibrary.org/obo/CL_…`).
- **CTann crosswalks** (`format: ctann-json`, `https://purl.humanatlas.io/ctann/<tool>`):
  - The PURL returns the processed digital object as JSON only when the request sends `Accept: application/json`.
  - The JSON has `$schema`, `@context`, `iri`, `metadata` and `data` at the top level. The mappings are in `data.mappings[]`, each with `subject_id`/`subject_label` (the tool's label), `object_id`/`object_label` (the CL term), `predicate_id` and `ext_organ_id`.
  - Every `object_id` is a CL ID. `predicate_id` can be `skos:exactMatch`, `skos:narrowMatch` or `skos:broadMatch`.
  - Stage 20 counts every predicate. To count exact matches only, filter on `predicate_id`.

## Plotting gotchas

- **UpSetPlot 0.9.0 does not work with pandas 3.** It fills missing styles with chained `fillna(..., inplace=True)`, which pandas 3's copy-on-write silently ignores, so `upset.plot()` crashes with `ValueError: Invalid RGBA argument: nan`.
  - `requirements.txt` therefore pins `pandas<3`; the data-preprocessor venv also uses 2.3.
  - With pandas 2 the same calls only print `FutureWarning`s, which stage 20 suppresses for `module="upsetplot"`.
- **UpSetPlot's `show_counts=True` also crashes** with numpy 2 and matplotlib 3.10+. Label bars with `ax.bar_label(ax.containers[0])` on `axes["intersections"]` and `axes["totals"]` instead, as `data-preprocessor/scripts/50-run-reports.py` does.
- **Fonts:**
  - The font is Arial (`plt.rcParams["font.family"]`). macOS ships it at `/System/Library/Fonts/Supplemental/Arial.ttf`; on a machine without Arial, matplotlib falls back to its default font with a warning.
  - All text except the title is 1.5× the default size: `font.size` 10 → 15 pt.
  - The title is 2× matplotlib's default figure title: 12 → 24 pt. `TITLE_PT` is computed *before* `font.size` is scaled, because `figure.titlesize` ("large") is relative to `font.size`. Computing it afterwards would give 36 pt.
- **Column order can change between runs.** The plot uses `sort_by="cardinality"`, and columns with equal counts (for example the two bars of 60) can swap places. The numbers stay the same.
- **Larger fonts crowd the 14×7 in figure.** Some total-bar labels run into their bars, and the left axis ticks almost touch. If that needs fixing, widen the figure or give the totals panel more room.

## Results snapshot (2026-11-16 downloads)

Unique CL IDs per file:

| File | Unique CL IDs |
|---|---|
| Azimuth crosswalk | 306 |
| CellTypist crosswalk | 268 |
| popV crosswalk | 157 |
| 2D FTU crosswalk | 137 |
| FR-Match crosswalk | 53 |
| All five combined | 542 |

- 14 CL IDs are in all five files.
- 60 of the 137 CL IDs in the 2D FTU crosswalk appear in none of the four CTann crosswalks.
- The largest single group is 114 CL IDs found only in the Azimuth crosswalk.

The PURLs always resolve to the latest version, so these numbers change when a crosswalk is updated. Re-run the pipeline rather than trusting this table.
