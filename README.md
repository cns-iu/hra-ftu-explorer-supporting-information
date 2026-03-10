# Supporting Information

## Instructions for running the `data-preprocessor` workflow

1. Navigate to the `data-preprocessor` folder:  
```bash
   cd data-preprocessor
```

2. Copy the files `sc-transcriptomics-cell-summaries.top10k.jsonl.gz` and `sc-transcriptomics-cell-instances.csv.gz` into the `raw-data` (create it if need be) and `input` folders, respectively.

3. Create the virtual environment and install dependencies
```bash
	python setup_and_run.py
```

4. Activate the virtual environment
```bash
source .venv/bin/activate
```
5. Deactivate when finished
```bash
deactivate

```