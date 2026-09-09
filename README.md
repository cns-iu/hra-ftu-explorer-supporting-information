# Supporting Information

## Instructions for running the `data-preprocessor` workflow

1. Navigate to the `data-preprocessor` folder:  
```bash
   cd data-preprocessor
```

2. Copy the files `sc-transcriptomics-cell-summaries.top10k.jsonl.gz` and `sc-transcriptomics-cell-instances.csv.gz` into the `raw-data` (create it if need be) and `input` folders, respectively.

3. Create the virtual environment, install dependencies, and run the pipeline scripts in order
```bash
python set_up_and_run.py
```

4. To re-run or debug an individual script afterward, activate the virtual environment first
```bash
source .venv/bin/activate
```
(on Windows: `.venv\Scripts\activate`), then run it directly, e.g. `python scripts/20-preprocess-hra-pop.py`.

5. Deactivate when finished
```bash
deactivate
```

## Instructions for running the `analysis` scripts

The `analysis` folder holds standalone scripts used to compute counts/tables for the paper. They read from `data-preprocessor`'s `output`/`input`/`raw-data` folders, so run the `data-preprocessor` workflow above first.

1. Navigate to the `analysis` folder:
```bash
cd analysis
```

2. Create the virtual environment and install dependencies (this does not run any script)
```bash
python setup_env.py
```

3. Activate the virtual environment
```bash
source .venv/bin/activate
```
(on Windows: `.venv\Scripts\activate`)

4. Run whichever script you need, e.g.
```bash
python SCRIPT_NAME.py
```
Results are written as CSVs to `analysis/output`.

5. Deactivate when finished
```bash
deactivate
```