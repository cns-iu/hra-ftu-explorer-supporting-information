import sys
from pathlib import Path

import pandas as pd
import yaml

# Helpers/config shared with data-preprocessor/ and analysis/general-analysis/, kept at the repo root
OVERLAP_DIR = Path(__file__).parent.parent  # this file is in analysis/overlap-analysis/scripts/
REPO_ROOT = OVERLAP_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from shared_common import *  # noqa: E402,F403

# Downloaded inputs (gitignored)
RAW_DATA_DIR = OVERLAP_DIR / "raw-data"
RAW_DATA_DIR.mkdir(exist_ok=True)

# Outputs
REPORTS_DIR = OVERLAP_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Inputs specific to this analysis (download URLs, Accept headers, local filenames).
# Named OVERLAP_CONFIG so it doesn't shadow the repo-root `config` from shared_common
OVERLAP_CONFIG_FILE = OVERLAP_DIR / "config.yaml"
with open(OVERLAP_CONFIG_FILE, "r", encoding="utf-8") as f:
    OVERLAP_CONFIG = yaml.safe_load(f)
DOWNLOADS = OVERLAP_CONFIG["downloads"]


def download_path(key: str) -> Path:
    """Local path of a downloaded input, by its key under `downloads` in config.yaml."""
    return RAW_DATA_DIR / DOWNLOADS[key]["filename"]
