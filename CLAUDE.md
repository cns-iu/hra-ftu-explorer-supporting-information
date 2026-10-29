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
  - `HRA_POP_VERSION` must be `v1.1` (not `v1.0`). Build every HRApop URL (`input-data/<version>/…`, `output-data/<version>/reports/…`) from `config['HRA_POP_BRANCH']`/`config['HRA_POP_VERSION']` rather than hardcoding a version. `ftu2-pseudo-code.md` still has outdated v1.0 links; don't copy them.
- `ANNOTATION_METHOD_PREFERENCE` / `method_rank`: the single order (azimuth, celltypist, popv, fr-match, pan-human-azimuth, author) for picking one annotation tool per dataset so cells are never counted twice. Both the pipeline (40/41) and `analysis/cell_types_and_datasets_per_ftu.py` use it.
- `load_json` and `iterate_through_json_lines` (JSONL reader; transparently handles gzipped `.jsonl.gz`, and intentionally does not pre-count lines before iterating — some inputs are tens of GB gzipped, so a full decompress-to-count pass before the real read would double the work).

Before this existed, both `shared.py` files had their own copy of `iterate_through_json_lines`, which drifted (only `analysis/`'s handled gzip and skipped the line pre-count) — don't reintroduce that by re-duplicating a function here instead of importing it.

### `data-preprocessor/` — the active pipeline

`scripts/shared.py` is imported (never executed) by every stage. It:
- Imports `config`/`load_json`/`iterate_through_json_lines` from the root `shared_common.py` (see above).
- Derives all path constants (`INPUT_DIR`, `OUTPUT_DIR`, `RAW_DATA_DIR`, `REPORTS_DIR`, and `TEMP_DIR`) relative to itself, then builds pipeline-specific file paths (`CELL_TYPES_IN_FTUS`, `FTU_DATASETS`, etc.) by joining those dirs to `config` values.
- `TEMP_DIR` = `docs/iftu-testing/assets` — pipeline outputs are written there so the GitHub Pages demo (see below) can load them directly; this is also where a production run would stage files before they're deposited into the `hra-ui` repo's `apps/ftu-ui/src/assets/TEMP/`.
- Holds pipeline-specific HTTP/JSONL helpers (`download_from_url`, `open_cell_type_populations`, `get_csv_pandas`, `fetch_grlc_csv_to_df`) and the FTU-exclusivity helpers (`get_organs_with_ftus`, `is_cell_type_exclusive_to_ftu`, `comes_from_organ_with_ftu`), the per-source filtering used by stages 20 and 25 (`identify_datasets_of_interest`, `filter_cell_summaries`), and the multi-source readers used by 40/41 (`iterate_filtered_cell_summaries`, `load_filtered_dataset_metadata`, `load_dataset_metadata`, all driven by `CELL_SUMMARY_SOURCES`; `iterate_preferred_cell_summaries` keeps only each dataset's preferred annotation tool), plus the heavy imports (`scanpy`, `anndata`, `matplotlib`, `upsetplot`) that keep this file out of `shared_common.py`.

Pipeline stages (`scripts/`, run in this numeric order):
1. `10-identify-cell-types-ftu-only.py` — queries `https://apps.humanatlas.io/api/grlc/hra/2d-ftu-parts.csv` for organs/FTUs, then the FTU-exclusive-CTs report, and writes `output/cell-types-in-ftus.json`: for every FTU, which cell types are exclusive to it (vs. shared with other anatomical structures) per the ASCT+B tables. This exclusivity list gates everything downstream — only cell type populations for these CTs are usable in the FTU Explorer.
2. `20-preprocess-hra-pop.py` — downloads the HRApop universe (`sc-transcriptomics-cell-summaries.jsonl.gz` + dataset metadata CSV) and atlas (`atlas-enriched-dataset-graph.jsonld`) per `config.yaml`'s `HRA_POP_VERSION`/`HRA_POP_BRANCH`, filters to datasets from organs with FTUs, and writes the filtered intermediary (`raw-data/cell_type_populations_intermediary.jsonl`) and `output/filtered-dataset-metadata.json` / `output/datasets-of-interest.json`.
3. `25-preprocess-anatomogram.py` — runs the same filter (`filter_cell_summaries`) over the committed anatomogram (EBI Single Cell Expression Atlas) data in the repo-root `anatomogram-data/` folder (kidney, liver, lung, pancreas; same JSONL/CSV formats as HRApop), writing `raw-data/anatomogram_cell_type_populations_intermediary.jsonl` and `output/anatomogram-filtered-dataset-metadata.json`. To add another source, give it its own preprocessing stage and add an entry to `CELL_SUMMARY_SOURCES` in `shared.py`; 40/41 read every entry.
4. `40-build-ftu-datasets-jsonld.py` — builds the dataset-metadata JSON-LD (`output/ftu-datasets.jsonld`, copied to `TEMP_DIR`) consumed by the FTU Explorer's `datasets` input — one `FtuIllustration` per FTU digital object listing its source datasets (label/link/authors/year).
5. `41-build-ftu-cell-summaries-jsonld.py` — builds the cell-summary JSON-LD (`output/ftu-cell-summaries.jsonld`, copied to `TEMP_DIR`) consumed by the Explorer's `summaries` input — per dataset, per exclusive cell type, mean gene expression values.
6. `50-run-reports.py` — sanity-check outputs only (not part of the deployed data path): CSV/plots in `reports/` (UpSet plot of cell-type overlap across FTUs, grouped bar chart of cell-type counts, a colliding-AS report).

There is no `30-*` or `60-*` script — `data-preprocessor/ftu2-pseudo-code.md` sketches a conceptually broader 10–60 pipeline (including anatomogram/SCEA ingestion for kidney/liver/lung/pancreas as steps 40/50 and a final `60-combine-all.py`), but the implemented scripts cover HRApop (20) and pre-computed anatomogram cell summaries (25). The older anatomogram scaffolding (`ANATOMOGRAMN_METADATA`/`ANATOMOGRAMN_RAW_DATA` in `config.yaml`, `anatomogram_files_json` in `shared.py`, `scripts/scratch/`) is for building those summaries from raw SCEA downloads and isn't used by stage 25. Check `ftu2-pseudo-code.md` before assuming a described step exists as code — much of it is still pseudocode/open questions, not implementation.

### More guidance in nested CLAUDE.md files

- `data-preprocessor/CLAUDE.md`: the output JSON-LD contract hra-ui expects, the minimum-cells rule, and duplicate-dataset exclusions.
- `analysis/CLAUDE.md`: setup and conventions for the standalone paper-analysis scripts.

## Domain notes worth knowing before editing the pipeline

(from `data-preprocessor/ftu2-pseudo-code.md`'s "Open questions and notes" — still open as of this writing)

- A cell type population qualifies for the FTU Explorer only if: its dataset's organ has an FTU, the CT is exclusive to that FTU (in the FTU illustration AND only connected to that FTU or its child in the organ's ASCT+B table), and the CT is crosswalked.
- The ASCT+B tables' own "FTU" column is unreliable as of HRA v2.3 — exclusivity must be (re)computed from the illustration + partonomy data, not read off that column directly.
- Skin is a known exception to the exclusivity rule (it has only one AS).
- The nephron contains five smaller FTUs (cortical collecting duct etc.), so its crosswalk mixes illustration nodes that are AS, not CT.
- Annotation-method preference order when multiple exist: organ-specific Azimuth, then CellTypist, popV, FR-Match, Pan-Human Azimuth, author labels (`ANNOTATION_METHOD_PREFERENCE` in `shared_common.py`). The pipeline picks among the tools that found FTU-exclusive CTs, because the intermediaries only contain those. The analysis script picks among all tools a dataset has, so the two can choose different tools for the same dataset.
