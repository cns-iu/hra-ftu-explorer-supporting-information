import sys
from pathlib import Path
from pprint import pprint
import anndata as ad
import pandas as pd

# Helpers/config shared with data-preprocessor/ and analysis/general-analysis/, kept at the repo root
ORAL_CAVITY_DIR = Path(
    __file__
).parent.parent  # this file is in analysis/oral-cavity-data-analysis/scripts/
REPO_ROOT = ORAL_CAVITY_DIR.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from shared_common import *  # noqa: E402,F403

# Downloaded inputs (gitignored)
RAW_DATA_DIR = ORAL_CAVITY_DIR / "raw-data"
RAW_DATA_DIR.mkdir(exist_ok=True)

# Outputs
REPORTS_DIR = ORAL_CAVITY_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
CXG_DATA_JSON = REPORTS_DIR / "oral-cavity-cxg-cell-types.json"

CROSSWALK_CSV_URL = "https://cdn.humanatlas.io/digital-objects/2d-ftu/asct-b-2d-models-crosswalk/latest/assets/asct-b-2d-models-crosswalk.csv"
SUPERTREE_URL = "https://raw.githubusercontent.com/cns-iu/hra-ctann-supporting-information/refs/heads/main/data/CTann-Supertree-v10.csv"
MOUTH_ID = "UBERON:0000165"

df_illustrations = pd.read_csv(CROSSWALK_CSV_URL, skiprows=11)
df_supertree = pd.read_csv(SUPERTREE_URL)
df_illustrations_mouth = (
    df_illustrations[df_illustrations["organ_id"] == MOUTH_ID][
        [
            "organ_label",
            "organ_id",
            "anatomical_structure_of",
            "label",
            "OntologyID",
        ]
    ]
    .drop_duplicates()
    .dropna()
)


def check_if_cell_id_in_df(cell_id: str, df: pd.DataFrame):
    exists = (df == cell_id).any().any()
    return bool(exists)


def save_to_json(data: dict):
    with open(CXG_DATA_JSON, "w") as f:
        json.dump(data, f, indent=4)
