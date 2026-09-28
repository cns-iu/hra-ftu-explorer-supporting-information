# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo purpose

Supporting information for the paper "Exploring Cell Types and Biomarker Expression Levels in 23 Functional Tissue Units Across 10 Organs in the Human Reference Atlas" (aka the "FTU2" paper) and its companion GitHub Pages site. The core deliverable is a data pipeline (`data-preprocessor/`) that produces the two JSON-LD files the [HRA FTU Explorer](https://github.com/hubmapconsortium/hra-ui) web component needs to render cell-by-gene data on FTU illustrations.

## Commands

Set up and run the pipeline from `data-preprocessor/`:

```bash
cd data-preprocessor
python set_up_and_run.py   # creates .venv, installs requirements.txt, then runs scripts/*.py in filename sort order
source .venv/bin/activate  # to run/debug an individual script afterward
deactivate
```

Note: `README.md` calls this `setup_and_run.py` (no underscore between "set" and "up") — the actual file is `set_up_and_run.py`.

Before running, place required inputs by hand (not committed, see `.gitignore`):
- `raw-data/sc-transcriptomics-cell-summaries.top10k.jsonl.gz`
- `input/sc-transcriptomics-cell-instances.csv.gz`

To run a single stage instead of the whole pipeline, activate the venv and run one script directly, e.g. `python scripts/20-preprocess-hra-pop.py`. Scripts other than `shared.py` are picked up by `set_up_and_run.py` in alphabetical/numeric filename order, so a new stage's numeric prefix determines execution order.

There is no lint/test suite in this repo currently.

## Architecture

### `shared_common.py` — repo root, shared by both `data-preprocessor/` and `analysis/`

Deliberately kept free of heavy/optional dependencies (no `scanpy`/`anndata`/`matplotlib`/`upsetplot`) so it's safe to import from the lightweight `analysis/` venv as well as the full pipeline venv. Both `data-preprocessor/scripts/shared.py` and `analysis/shared.py` add the repo root to `sys.path` and `from shared_common import ...` rather than defining their own copies — do the same for any new helper both sides would otherwise duplicate. It holds:
- Loading `config.yaml` (repo root) into `config` — the single source of truth for every input/output filename and the FTU-exclusivity SPARQL query URL. Add new filenames there, not as string literals in a script.
- `load_json` and `iterate_through_json_lines` (JSONL reader; transparently handles gzipped `.jsonl.gz`, and intentionally does not pre-count lines before iterating — some inputs are tens of GB gzipped, so a full decompress-to-count pass before the real read would double the work).

Before this existed, both `shared.py` files had their own copy of `iterate_through_json_lines`, which drifted (only `analysis/`'s handled gzip and skipped the line pre-count) — don't reintroduce that by re-duplicating a function here instead of importing it.

### `data-preprocessor/` — the active pipeline

`scripts/shared.py` is imported (never executed) by every stage. It:
- Imports `config`/`load_json`/`iterate_through_json_lines` from the root `shared_common.py` (see above).
- Derives all path constants (`INPUT_DIR`, `OUTPUT_DIR`, `RAW_DATA_DIR`, `REPORTS_DIR`, and `TEMP_DIR`) relative to itself, then builds pipeline-specific file paths (`CELL_TYPES_IN_FTUS`, `FTU_DATASETS`, etc.) by joining those dirs to `config` values.
- `TEMP_DIR` = `docs/iftu-testing/assets` — pipeline outputs are written there so the GitHub Pages demo (see below) can load them directly; this is also where a production run would stage files before they're deposited into the `hra-ui` repo's `apps/ftu-ui/src/assets/TEMP/`.
- Holds pipeline-specific HTTP/JSONL helpers (`download_from_url`, `open_cell_type_populations`, `get_csv_pandas`, `fetch_grlc_csv_to_df`) and the FTU-exclusivity helpers (`get_organs_with_ftus`, `is_cell_type_exclusive_to_ftu`, `comes_from_organ_with_ftu`), plus the heavy imports (`scanpy`, `anndata`, `matplotlib`, `upsetplot`) that keep this file out of `shared_common.py`.

Pipeline stages (`scripts/`, run in this numeric order):
1. `10-identify-cell-types-ftu-only.py` — queries `https://apps.humanatlas.io/api/grlc/hra/2d-ftu-parts.csv` for organs/FTUs, then the FTU-exclusive-CTs report, and writes `output/cell-types-in-ftus.json`: for every FTU, which cell types are exclusive to it (vs. shared with other anatomical structures) per the ASCT+B tables. This exclusivity list gates everything downstream — only cell type populations for these CTs are usable in the FTU Explorer.
2. `20-preprocess-hra-pop.py` — downloads the HRApop universe (`sc-transcriptomics-cell-summaries.jsonl.gz` + dataset metadata CSV) and atlas (`atlas-enriched-dataset-graph.jsonld`) per `config.yaml`'s `HRA_POP_VERSION`/`HRA_POP_BRANCH`, filters to datasets from organs with FTUs, and writes the filtered intermediary (`raw-data/cell_type_populations_intermediary.jsonl`) and `output/filtered-dataset-metadata.json` / `output/datasets-of-interest.json`.
3. `40-build-ftu-datasets-jsonld.py` — builds the dataset-metadata JSON-LD (`output/ftu-datasets.jsonld`, copied to `TEMP_DIR`) consumed by the FTU Explorer's `datasets` input — one `FtuIllustration` per FTU digital object listing its source datasets (label/link/authors/year).
4. `41-build-ftu-cell-summaries-jsonld.py` — builds the cell-summary JSON-LD (`output/ftu-cell-summaries.jsonld`, copied to `TEMP_DIR`) consumed by the Explorer's `summaries` input — per dataset, per exclusive cell type, mean gene expression values.
5. `50-run-reports.py` — sanity-check outputs only (not part of the deployed data path): CSV/plots in `reports/` (UpSet plot of cell-type overlap across FTUs, grouped bar chart of cell-type counts, a colliding-AS report).

There is no `30-*` or `60-*` script — `data-preprocessor/ftu2-pseudo-code.md` sketches a conceptually broader 10–60 pipeline (including anatomogram/SCEA ingestion for kidney/liver/lung/pancreas as steps 40/50 and a final `60-combine-all.py`), but the implemented scripts only cover the HRApop-derived path so far; anatomogram support (`ANATOMOGRAMN_METADATA`/`ANATOMOGRAMN_RAW_DATA` in `config.yaml`, `anatomogram_files_json` in `shared.py`) is scaffolded but not yet wired into a numbered stage. Check `ftu2-pseudo-code.md` before assuming a described step exists as code — much of it is still pseudocode/open questions, not implementation.

### Output JSON-LD contract

Both output files must match what `hra-ftu-ui` expects (see full examples in `ftu2-pseudo-code.md`):
- `ftu-cell-summaries.jsonld`: `@graph` of `CellSummary` objects keyed by `cell_source` (a dataset DOI or entity URL fragment), each with a `summary` array of `CellSummaryRow` (`cell_id`, `cell_label`, `genes[]` with `ensemble_id`/`gene_id`/`gene_label`/`mean_expression`).
- `ftu-datasets.jsonld`: `@graph` of `FtuIllustration` objects (`@id` = `https://purl.humanatlas.io/2d-ftu/<organ>-<ftu>`) each with `data_sources[]` (`Dataset` with label/link/description/year/authors).

### `docs/` — GitHub Pages demo site

Jekyll site (`_config.yml`, kramdown). Two standalone demo pages, both embedding a `hra-ui` web component directly via CDN script tags (no build step):
- `docs/index.md` / `docs/iftu-testing/` — full `<hra-ftu-ui>` component reading `assets/ftu-datasets.jsonld` / `assets/ftu-cell-summaries.jsonld`, i.e. the live pipeline output described above.
- `docs/iftu-fixes/` — `<hra-ftu-ui-small>` component for testing FTU illustration SVG fixes in isolation (`assets/ftu-illustrations.jsonld` + local `2d-ftu-*.svg` files), reusing datasets/summaries from `../iftu-testing/assets/`.

### `analysis/` — standalone paper-analysis scripts

Independent, on-demand scripts that compute counts/tables for the paper (not a sequential pipeline, unlike `data-preprocessor/`). One shared venv/`requirements.txt` for all of them.

```bash
cd analysis
python setup_env.py         # creates .venv, installs requirements.txt (does NOT run any script)
source .venv/bin/activate
python <your_script>.py     # each script is run independently, on demand
```

- `shared.py` — import (don't run) for common helpers: imports `config`/`load_json`/`iterate_through_json_lines` from the root `shared_common.py`; `DATA_PROCESSOR`/`RAW_DATA_DIR` point at `data-preprocessor/` and its `raw-data/` folder (read-only from here — run that pipeline first if they're empty); `FTU_QUERY` and `UNIVERSE_10K_FILENAME` are paths/URLs built from `config`; `save_df(df, file_name)` writes a CSV to `output/`. Follow the same pattern for any new pipeline output file you need: join `DATA_PROCESSOR`'s output dir to `config["SOME_KEY"]` rather than hardcoding a filename.
- `output/` — where scripts should save their results (CSVs of counts/tables), committed for reproducibility.
- New scripts: give them descriptive names (no numeric prefix — they aren't ordered pipeline stages), add any new dependency to `analysis/requirements.txt`.

### `archive/`

Pre-`data-preprocessor` exploratory notebooks/scripts and CSV data products (ASCT+B tables, vasculature biomarker analysis, old sankey diagrams) — superseded by `data-preprocessor/`, kept for reference only, not run as part of any current workflow.

## Domain notes worth knowing before editing the pipeline

(from `data-preprocessor/ftu2-pseudo-code.md`'s "Open questions and notes" — still open as of this writing)

- A cell type population qualifies for the FTU Explorer only if: its dataset's organ has an FTU, the CT is exclusive to that FTU (in the FTU illustration AND only connected to that FTU or its child in the organ's ASCT+B table), and the CT is crosswalked.
- The ASCT+B tables' own "FTU" column is unreliable as of HRA v2.3 — exclusivity must be (re)computed from the illustration + partonomy data, not read off that column directly.
- Skin is a known exception to the exclusivity rule (it has only one AS).
- The nephron contains five smaller FTUs (cortical collecting duct etc.), so its crosswalk mixes illustration nodes that are AS, not CT.
- Annotation-method preference order when multiple exist: organ-specific Azimuth, then CellTypist, then popV.
