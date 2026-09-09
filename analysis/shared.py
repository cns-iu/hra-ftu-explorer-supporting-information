# commonly used packages/helpers for analysis scripts
import gzip
import json
from pathlib import Path

import pandas as pd

# This folder
ANALYSIS_DIR = Path(__file__).parent

# Where analysis scripts should write their results (counts, tables, figures)
OUTPUT_DIR = ANALYSIS_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# The data-preprocessor pipeline's own folders, read-only from here.
# Run data-preprocessor/set_up_and_run.py first if these are empty.
DATA_PREPROCESSOR_DIR = ANALYSIS_DIR.parent / "data-preprocessor"
PIPELINE_INPUT_DIR = DATA_PREPROCESSOR_DIR / "input"
PIPELINE_OUTPUT_DIR = DATA_PREPROCESSOR_DIR / "output"
PIPELINE_RAW_DATA_DIR = DATA_PREPROCESSOR_DIR / "raw-data"


def load_json(file_path: str | Path):
    """Load a .json/.jsonld file into a dict/list."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(file_path: str | Path):
    """Yield one dict per line from a .jsonl or gzipped .jsonl.gz file."""
    file_path = Path(file_path)
    opener = gzip.open if file_path.suffix == ".gz" else open
    with opener(file_path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def save_df(df: pd.DataFrame, file_name: str):
    """Save a counts/summary table to analysis/output as CSV."""
    out_path = OUTPUT_DIR / file_name
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")
    return out_path
