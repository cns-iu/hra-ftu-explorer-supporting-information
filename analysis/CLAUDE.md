# CLAUDE.md

Guidance for working in `analysis/`. The repo-wide overview is in the root `CLAUDE.md`.

### `analysis/` — standalone paper-analysis scripts

Independent, on-demand scripts that compute counts/tables for the paper (not a sequential pipeline, unlike `data-preprocessor/`). One shared venv/`requirements.txt` for all of them.

```bash
cd analysis
python setup_env.py         # creates .venv, installs requirements.txt (does NOT run any script)
source .venv/bin/activate
python <your_script>.py     # each script is run independently, on demand
```

- `shared.py` — import (don't run) for common helpers: imports `config`/`load_json`/`iterate_through_json_lines` from the root `shared_common.py`; `DATA_PROCESSOR`/`RAW_DATA_DIR` point at `data-preprocessor/` and its `raw-data/` folder (read-only from here — run that pipeline first if they're empty); `FTU_QUERY` and `UNIVERSE_10K_FILENAME` are paths/URLs built from `config`; `save_df(df, file_name)` writes a CSV to `output/`. Follow the same pattern for any new pipeline output file you need: join `DATA_PROCESSOR`'s output dir to `config["SOME_KEY"]` rather than hardcoding a filename.
- `UNIVERSE_SANKEY_URL` (from `config['UNIVERSE_SANKEY_FILENAME']`) is HRApop's `universe-ad-hoc/sankey.csv` report, the source for dataset → paper DOI (`dataset_id`, `doi` columns). It has one row per dataset *per collision*, so drop duplicates on `dataset_id` first. Each dataset has at most one DOI, and many have none. DOI formats are mixed (`https://doi.org/…` vs `http://dx.doi.org/…`), and some HCA `dataset_id`s start with a literal `hhttps://` typo. Join on the raw strings. It hasn't been checked whether those typo'd IDs match the universe's `cell_source`, so check that before "fixing" them.
- `cell_types_and_datasets_per_ftu.py` — per FTU and per condition (`in_2d_ftu`/`in_asctb`/`exclusive_ct_in_ftu`): CT lists, dataset/cell counts from the HRApop universe (one annotation tool per dataset, chosen by `ANNOTATION_METHOD_PREFERENCE`), and `papers_for_this_ftu_by_dataset[condition] = {dataset_id: doi|null}`, which covers exactly the counted datasets. A full scan of the top10k universe file takes hours (about 5 records/s), so pass `sample_size` to `parse_universe_cell_summaries` for quick tests.
- `output/` — where scripts should save their results (CSVs of counts/tables), committed for reproducibility.
- New scripts: give them descriptive names (no numeric prefix — they aren't ordered pipeline stages), add any new dependency to `analysis/requirements.txt`.
