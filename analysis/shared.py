# commonly used packages/helpers for analysis scripts
import json
from pathlib import Path
from pprint import pprint

import pandas as pd

# Helpers/config shared with data-preprocessor/scripts/shared.py, kept at the repo root
import sys

ANALYSIS_DIR = Path(__file__).parent
REPO_ROOT = ANALYSIS_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from shared_common import config, load_json, iterate_through_json_lines, iri_to_curie  # noqa: E402

# Folders
DATA_PROCESSOR = REPO_ROOT / "data-preprocessor"
RAW_DATA_DIR = DATA_PROCESSOR / "raw-data"

# Output for analysis scripts
OUTPUT_DIR = ANALYSIS_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Query result to check unique CTs for FTUs
FTU_QUERY = config["FTU_QUERY"]

# HRApop universe sample (top10k genes per cell type), gzipped JSONL
UNIVERSE_10K_FILENAME = RAW_DATA_DIR / config["UNIVERSE_10K_FILENAME"]

# HRApop universe dataset metadata (dataset_id -> organ etc.), same source as data-preprocessor/scripts/20-*.py
UNIVERSE_METADATA_URL = (
    f"https://raw.githubusercontent.com/x-atlas-consortia/hra-pop/refs/heads/{config['HRA_POP_BRANCH']}"
    f"/input-data/{config['HRA_POP_VERSION']}/{config['UNIVERSE_METADATA_FILENAME']}"
)


def save_df(df: pd.DataFrame, file_name: str):
    """Save a counts/summary table to analysis/output as CSV."""
    out_path = OUTPUT_DIR / file_name
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")
    return out_path


def save_json(data, file_name: str):
    """Save a dict/list to analysis/output as JSON."""
    out_path = OUTPUT_DIR / file_name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {out_path}")
    return out_path
