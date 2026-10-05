"""Helpers shared between data-preprocessor/scripts/shared.py and analysis/shared.py.

Keep this free of heavy/optional dependencies (scanpy, anndata, matplotlib, upsetplot,
ujson, ...) so it stays safe to import from the lightweight analysis/ venv.
"""

import gzip
import json
from pathlib import Path
from pprint import pprint

import yaml
from tqdm import tqdm

REPO_ROOT = Path(__file__).parent
CONFIG_FILE = REPO_ROOT / "config.yaml"

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


def load_json(file_path: str | Path):
    """Load a .json/.jsonld file into a dict/list."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# A dataset can have one cell summary per annotation method (tool). To never count
# the same cells twice, each dataset is used with exactly one tool: the first one
# in this order that the dataset has a cell summary for. "author" (the original
# authors' labels, anatomogram data only) is a last resort
ANNOTATION_METHOD_PREFERENCE = (
    "azimuth",
    "celltypist",
    "popv",
    "fr-match",
    "pan-human-azimuth",
    "author",
)


def normalize_method(method: str) -> str:
    """Compare tool names ignoring case and separators (e.g. "FR-Match" == "fr_match")."""
    return "".join(char for char in method.lower() if char.isalnum())


def method_rank(method: str) -> int:
    """Position of a tool in ANNOTATION_METHOD_PREFERENCE; unknown tools rank last."""
    preference = [normalize_method(m) for m in ANNOTATION_METHOD_PREFERENCE]
    method = normalize_method(method)
    return preference.index(method) if method in preference else len(preference)


def iri_to_curie(iri: str) -> str:
    """Replace an IRI with a compact URI (CURIE)"""
    return iri.rsplit("/", 1)[-1].replace("_", ":")


def iterate_through_json_lines(filename: str, print_line: bool = False):
    """Iterate through a JSON Lines (JSONL) file and yield each JSON object.

    Transparently handles gzipped (.jsonl.gz) files. Skips an upfront line-count
    pass (no fixed total/ETA on the progress bar) since some inputs are tens of GB
    gzipped, making a full pre-count pass (decompressing the whole file just to
    count lines, before decompressing it again to process) too expensive.
    """
    filename = Path(filename)
    opener = gzip.open if filename.suffix == ".gz" else open

    print(
        f"Now processing {filename}, printing {'enabled' if print_line else 'not enabled'}."
    )

    with opener(filename, "rt", encoding="utf-8") as f:
        for line in tqdm(f, desc="Processing JSONL lines", unit="line"):
            line = line.strip()
            if not line:
                continue
            line_json = json.loads(line)
            if print_line:
                pprint(line_json)
            yield line_json
