# `analysis`

Standalone scripts that compute counts and tables for the FTU2 paper. Unlike `data-preprocessor/`, this is not a pipeline that runs in order: you run each script on its own, when you need it.

## Setup

```bash
cd analysis
python setup_env.py        # creates .venv and installs requirements.txt (doesn't run any script)
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
python <script>.py
deactivate
```

### Inputs

- `../data-preprocessor/raw-data/sc-transcriptomics-cell-summaries.top10k.jsonl.gz`: the HRApop universe cell summaries. This file isn't committed, so put it there by hand. The scripts here only read from `data-preprocessor/` and never write to it.
- These are downloaded at run time. Their URLs are built from `HRA_POP_BRANCH` / `HRA_POP_VERSION` (currently `v1.1`) in `../config.yaml`:
  - `FTU_QUERY`: CTs per FTU illustration and ASCT+B table, with an FTU-exclusivity flag
  - `UNIVERSE_METADATA_URL`: HRApop universe dataset metadata (`dataset_id` → organ)
  - `UNIVERSE_SANKEY_URL`: HRApop `universe-ad-hoc/sankey.csv` report (`dataset_id` → paper DOI)

## Scripts

### `cell_types_and_datasets_per_ftu.py`

For every FTU, the script reports results under three conditions:

- `in_2d_ftu`: the cell type (CT) is in the FTU illustration
- `in_asctb`: the CT is in the organ's ASCT+B table
- `exclusive_ct_in_ftu`: the CT is exclusive to the FTU

Under each condition it gives:

- the CTs that satisfy the condition (label, IRI, CURIE)
- the number of HRApop universe datasets from the FTU's organ that contain such a CT, and the number of cells of those CTs
- the paper DOI of each of those datasets, stored as `papers_for_this_ftu_by_dataset[condition] = {dataset_id: doi | null}`

Datasets can have one cell summary per annotation tool. So that the same cells are never counted twice, each dataset is counted from a single tool, the first one in `ANNOTATION_METHOD_PREFERENCE` (Azimuth → CellTypist → popV → …) that the dataset has a summary for.

A full scan of the universe file takes hours. For a quick test, pass `sample_size` to `parse_universe_cell_summaries`.

Outputs (in `output/`):

| File | Contents |
| --- | --- |
| `ftu_ct_conditions.json` | Full per-FTU dictionary: organ, CT lists, dataset and cell counts, and papers per condition |
| `ftu_ct_conditions.csv` | One row per FTU: CT count and labels, dataset/cell counts, and the number of distinct papers and their DOIs per condition |
| `cell_types_and_datasets_per_ftu.csv` | CTs in each illustration vs. exclusive CTs, per FTU |

## Adding a script

- Give it a descriptive name, with no numeric prefix.
- Start it with `from shared import *` to get `config`, the path/URL constants, `iterate_through_json_lines`, `save_df` and `save_json`.
- Add new filenames and URLs to `../config.yaml` rather than writing them into the script.
- Save results to `output/` (committed, for reproducibility).
- Add new dependencies to `requirements.txt`.
