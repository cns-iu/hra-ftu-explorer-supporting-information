# commonly used packages in this workflow
from pprint import pprint
import yaml
import requests
import pandas as pd
from io import StringIO
import json
from pathlib import Path
import gzip
from tqdm import tqdm
import os
import copy
import shutil
import ujson
import re
from collections import defaultdict
import scanpy as sc
import anndata as ad

# Make folder for input data
INPUT_DIR = Path(__file__).parent.parent / "input"
INPUT_DIR.mkdir(exist_ok=True)  # create the folder if it doesn't exist

# Make folder for output data
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)  # create the folder if it doesn't exist

# Make folder for reports
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)  # create the folder if it doesn't exist

# Make folder for raw data
RAW_DATA_DIR = (
    Path(__file__).parent.parent / "raw-data"
)  # for files larger than 100 MB, move HRApop data here as needed
RAW_DATA_DIR.mkdir(exist_ok=True)  # create the folder if it doesn't exist

# Capture script folder
SCRIPT_DIR = Path(__file__).parent

# Capture TEMP folder
TEMP_DIR = Path(__file__).parent.parent.parent / "docs" / "iftu-testing" / "assets"

# Load config file
with open(Path(__file__).parent / "config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Get HRApop metadata
hra_pop_version = config["HRA_POP_VERSION"]
hra_pop_branch = config["HRA_POP_BRANCH"]

# Assign file paths to constants
CELL_TYPES_IN_FTUS = OUTPUT_DIR / config["CELL_TYPES_IN_FTUS"]
UNIVERSE_FILE_FILENAME = INPUT_DIR / config["UNIVERSE_FILE_FILENAME"]
UNIVERSE_METADATA_FILENAME = INPUT_DIR / config["UNIVERSE_METADATA_FILENAME"]
UNIVERSE_10K_FILENAME = RAW_DATA_DIR / config["UNIVERSE_10K_FILENAME"]
ATLAS_FILE_FILENAME = INPUT_DIR / config["ATLAS_FILE_FILENAME"]
FTU_DATASETS_RAW_FILENAME = OUTPUT_DIR / config["FTU_DATASETS_RAW_FILENAME"]
FTU_CELL_SUMMARIES_RAW_FILENAME = OUTPUT_DIR / config["FTU_CELL_SUMMARIES_RAW_FILENAME"]
FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME = (
    RAW_DATA_DIR / config["FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME"]
)
FILTERED_DATASET_METADATA_FILENAME = (
    OUTPUT_DIR / config["FILTERED_DATASET_METADATA_FILENAME"]
)

FTU_DATASETS = OUTPUT_DIR / config["FTU_DATASETS"]
FTU_CELL_SUMMARIES = OUTPUT_DIR / config["FTU_CELL_SUMMARIES"]

FTU_DATASETS_OUTPUT = TEMP_DIR / config["FTU_DATASETS"]
FTU_CELL_SUMMARIES_OUTPUT = TEMP_DIR / config["FTU_CELL_SUMMARIES"]
ANATOMOGRAMN_METADATA = INPUT_DIR / config["ANATOMOGRAMN_METADATA"]
ANATOMOGRAMN_RAW_DATA = RAW_DATA_DIR / config["ANATOMOGRAMN_RAW_DATA"]

# Commonly used HTTP Accept headers for API requests
accept_json = {"Accept": "application/json"}
accept_csv = {"Accept": "text/csv"}

# Metadata for anatomogram datasets
anatomogram_files_json = [
    {
        "name": "kidney",
        "organ_id": "http://purl.obolibrary.org/obo/UBERON_0002113",
        "url_counts": "https://www.ebi.ac.uk/gxa/sc/experiment/E-CURD-119/download/zip?fileType=normalised",
        "url_experimental_design": "https://www.ebi.ac.uk/gxa/sc/experiment/E-CURD-119/download?fileType=experiment-design",
        "experiment_id": "E-CURD-119",
        "paper_doi": "https://doi.org/10.1038/s41467-021-22368-w",
        "dataset_link": "https://www.ebi.ac.uk/gxa/sc/experiments/E-CURD-119/downloads",
    },
    {
        "name": "liver",
        "organ_id": "http://purl.obolibrary.org/obo/UBERON_0002107",
        "url_counts": "https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-10553/download/zip?fileType=normalised",
        "url_experimental_design": "https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-10553/download?fileType=experiment-design",
        "experiment_id": "E-MTAB-10553",
        "paper_doi": "https://doi.org/10.1038/s41598-021-98806-y",
        "dataset_link": "https://www.ebi.ac.uk/gxa/sc/experiments/E-MTAB-10553/downloads",
    },
    {
        "name": "lung",
        "organ_id": "http://purl.obolibrary.org/obo/UBERON_0002048",
        "url_counts": "https://www.ebi.ac.uk/gxa/sc/experiment/E-GEOD-130148/download/zip?fileType=normalised",
        "url_experimental_design": "https://www.ebi.ac.uk/gxa/sc/experiment/E-GEOD-130148/download?fileType=experiment-design",
        "experiment_id": "E-GEOD-130148",
        "paper_doi": "https://doi.org/10.1038/s41591-019-0468-5",
        "dataset_link": "https://www.ebi.ac.uk/gxa/sc/experiments/E-GEOD-130148/downloads",
    },
    {
        "name": "pancreas",
        "organ_id": "http://purl.obolibrary.org/obo/UBERON_0001264",
        "url_counts": "https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-5061/download/zip?fileType=normalised",
        "url_experimental_design": "https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-5061/download?fileType=experiment-design",
        "experiment_id": "E-MTAB-5061",
        "paper_doi": "https://doi.org/10.1016/j.cmet.2016.08.020",
        "dataset_link": "https://www.ebi.ac.uk/gxa/sc/experiments/E-MTAB-5061/downloads",
    },
]

# Download links for anatomogram data:
# 1. Kidney: https://www.ebi.ac.uk/gxa/sc/experiment/E-CURD-119/download/zip?fileType=normalised
# 2. Liver: https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-10553/download/zip?fileType=normalised
# 3. Lung: https://www.ebi.ac.uk/gxa/sc/experiment/E-GEOD-130148/download/zip?fileType=normalised
# 4. Pancreas: https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-5061/download/zip?fileType=normalised

# Experimental design files:
# 1. Kidney: https://www.ebi.ac.uk/gxa/sc/experiment/E-CURD-119/download?fileType=experiment-design
# 2. Liver: https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-10553/download?fileType=experiment-design
# 3. Lung: https://www.ebi.ac.uk/gxa/sc/experiment/E-GEOD-130148/download?fileType=experiment-design
# 4. Pancreas: https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-5061/download?fileType=experiment-design

# SCEA websites:
# 1. Kidney: https://www.ebi.ac.uk/gxa/sc/experiments/E-CURD-119/downloads
# 2. Liver: https://www.ebi.ac.uk/gxa/sc/experiments/E-MTAB-10553/downloads
# 3. Lung: https://www.ebi.ac.uk/gxa/sc/experiments/E-GEOD-130148/downloads
# 4. Pancreas: https://www.ebi.ac.uk/gxa/sc/experiments/E-MTAB-5061/downloads


def get_csv_pandas(url: str, timeout: int = 10) -> pd.DataFrame:
    """
    Fetch a CSV file from a URL and return it as a pandas DataFrame.

    Args:
        url (str): The URL to the CSV file.
        timeout (int, optional): Timeout in seconds for the HTTP request. Defaults to 10.

    Returns:
        pd.DataFrame: DataFrame parsed from the CSV content.

    Raises:
        requests.exceptions.RequestException: If the HTTP request fails.
        ValueError: If the response cannot be parsed as CSV.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx, 5xx)

        # More permissive Content-Type check
        content_type = response.headers.get("Content-Type", "").lower()
        if not any(
            ct in content_type
            for ct in ("text/csv", "text/plain", "application/octet-stream")
        ):
            raise ValueError(f"Unexpected Content-Type: {content_type}")

        # Parse CSV
        return pd.read_csv(StringIO(response.text))

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch CSV from {url}") from e
    except pd.errors.ParserError as e:
        raise ValueError(f"Failed to parse CSV from {url}") from e


def download_from_url(
    url: str, base_dir: str | Path = None, output_file: str = ""
) -> Path:
    """
    Download a gzipped JSONL file or a CSV and save it locally,
    showing a progress bar while streaming.

    Args:
        url (str): The URL of the file to download.
        base_dir (str | Path, optional): The base directory where the file should be stored.
            Defaults to INPUT_DIR if not provided. Can be RAW_DIR, INPUT_DIR, or any other folder.
        output_file (str): The filename or relative path to save the downloaded file as.

    Returns:
        Path: The path to the downloaded (or existing) file.

    Raises:
        HTTPError: If the HTTP request for the URL fails.
        OSError: If writing to the local file path fails.
    """
    base_dir = Path(base_dir or INPUT_DIR)
    file_path = base_dir / output_file

    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        print(f"ℹ️ File already exists at {file_path}, skipping download.")
        return file_path

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total_size = int(r.headers.get("content-length", 0))

        with open(file_path, "wb") as f, tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            desc=file_path.name,
            ascii=True,
        ) as pbar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

    print(f"✅ File with URL {url} saved to {file_path}")
    return file_path


def open_cell_type_populations(file_path: str):
    """
    Open and parse a cell type population file in JSON or gzipped JSONL format.

    If the file is gzipped JSONL (.jsonl.gz), the function returns a generator
    that yields one record at a time (streaming, suitable for large files).

    If the file is a regular JSON file (.json, .jsonld, etc.), the function loads
    the entire file into memory and returns it as a Python object (dict or list).

    Args:
        file_path (str): Path to the input file.

    Returns:
        generator: Yields dicts line by line if the file is gzipped JSONL.
        dict | list: Parsed JSON object if the file is a standard JSON file.

    Raises:
        OSError: If the file cannot be opened.
        json.JSONDecodeError: If the file contents are not valid JSON.
    """

    if is_gzipped(file_path):

        def record_generator():
            with gzip.open(file_path, "rt", encoding="utf-8") as f:
                for line in f:
                    yield json.loads(line)

        return record_generator()
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)


def is_gzipped(path_or_url: str) -> bool:
    """
    Determine whether a local file or a remote URL is gzipped.

    For local files:
        - Opens the file in binary mode and inspects the first two bytes.
        - A gzipped file always begins with the magic number 0x1f 0x8b.

    For URLs:
        - Checks the Content-Type and Content-Encoding headers for 'gzip'.
        - If headers are inconclusive, streams the first two bytes and
          inspects them for the gzip magic number.

    Args:
        path_or_url (str): Path to a local file or URL to check.

    Returns:
        bool: True if the file or URL points to a gzipped resource, False otherwise.

    Raises:
        OSError: If the local file cannot be opened.
        requests.RequestException: If the URL cannot be reached.
    """
    if path_or_url.startswith(("http://", "https://")):
        # Try headers first
        head = requests.head(path_or_url, allow_redirects=True)
        ctype = head.headers.get("Content-Type", "").lower()
        cenc = head.headers.get("Content-Encoding", "").lower()
        if "gzip" in ctype or "gzip" in cenc:
            return True

        # Fallback: peek at first bytes
        with requests.get(path_or_url, stream=True) as r:
            r.raise_for_status()
            return r.raw.read(2) == b"\x1f\x8b"
    else:
        # Local file check
        file_path = Path(path_or_url)
        with open(file_path, "rb") as f:
            return f.read(2) == b"\x1f\x8b"


def get_organs_with_ftus():
    """Retrieves a list of FTUs and their parts via the HRA API and a SPARQL query

    Returns:
        organs_with_ftus (list): A list of organs with their FTUs
    """

    df = get_csv_pandas("https://apps.humanatlas.io/api/grlc/hra/2d-ftu-parts.csv")
    
    # Ok, on staging, those two would look like:
    # https://apps.humanatlas.io/api/grlc/hra/2d-ftu-parts.csv?endpoint=https://apps.humanatlas.io/api--staging/v1/sparql
    # https://apps.humanatlas.io/api--staging/kg/digital-objects
    # I wouldn't switch to those yet. staging hasn't been updated with the latest changes.
    # (grlc endpoints can be transformed like above for staging for reasons)

    # Loop through df and identify organs and their FTUs
    organs_with_ftus = []

    for (organ_label, organ_id), group in df.groupby(["organ_label", "organ_iri"]):
        organ_dict = {
            "organ_label": organ_label,
            "organ_id": organ_id,
            "ftu": group[["ftu_iri", "ftu_digital_object"]]
            .drop_duplicates()
            .to_dict(orient="records"),  # list of dicts
        }
        organs_with_ftus.append(organ_dict)

    return organs_with_ftus


def comes_from_organ_with_ftu(
    organ_id_to_check: str | None, cell_types_in_ftus: list
) -> bool:
    """
    Determine whether a given organ ID corresponds to an organ that has
    FTUs (Functional Tissue Units).

    Args:
        check_organ_id (str | None): The short organ ID to check. If None, the function returns False.
        cell_types_in_ftu (list): A list of dictionaries describing cell types in FTUs,
            where each dictionary is expected to contain an 'organ_id_short' key.

    Returns:
        bool: True if the provided organ ID corresponds to an organ that has FTUs,
        False otherwise.
    """
    if organ_id_to_check is None:
        return False

    return organ_id_to_check in {ftu["organ_id_short"] for ftu in cell_types_in_ftus}


# def build_ftu_index(cell_types_in_ftus):
#     index = defaultdict(list)
#     for ftu in cell_types_in_ftus:
#         organ = ftu["organ_id_short"]
#         iri = ftu["iri"]
#         for ct in ftu.get("cell_types_in_ftu_only", ()):
#             index[(organ, ct["representation_of"])].append(iri)
#     return index


# def is_cell_type_exclusive_to_ftu(cell_id_to_check, organ_id_to_check, index):
#     """
#     Retrieve all FTU IRIs where a given cell type is exclusive within a specific organ.

#     Args:
#         cell_id_to_check (str): The cell type identifier to look up (e.g., a CL or UBERON ID).
#         organ_id_to_check (str): The short-form organ ID (e.g., 'UBERON:0002107') corresponding
#             to the organ being checked.
#         index (dict[tuple[str, str], list[str]]): A precomputed lookup mapping
#             (organ_id_short, cell_id) tuples to lists of FTU IRIs, typically built by
#             `build_ftu_index()`.

#     Returns:
#         list[tuple[str, str]]: A list of (cell_id_to_check, ftu_iri) tuples for all matching FTUs.
#         Returns an empty list if no matches are found.
#     """

#     return [
#         (cell_id_to_check, iri)
#         for iri in index.get((organ_id_to_check, cell_id_to_check), ())
#     ]

# slower alternative:


def is_cell_type_exclusive_to_ftu(
    cell_id_to_check: str | None, organ_id_to_check: str, cell_types_in_ftu: list[dict]
) -> list:
    """
    Determine whether a given cell type (by ID) is exclusive to Functional Tissue Units (FTUs).

    Args:
        cell_id_to_check (str | None): The cell type ID to check. If None, returns False.
        cell_types_in_ftu (list[dict]): A list of FTU dictionaries, each containing a
            'cell_types_in_ftu_only' key with a list of cell type dictionaries.
            Each cell type dictionary must contain a 'representation_of' key.

    Returns:
        bool: True if the given cell type appears in any 'cell_types_in_ftu_only' list,
        False otherwise.
    """
    if cell_id_to_check is None:
        return []

    # print(f"Now checking {cell_id_to_check} in {organ_id_to_check}.")

    # Iterate over all FTUs and collect all "representation_of" IDs for CTs in "cell_types_in_ftu_only"
    matches = [
        (ct["representation_of"], ftu["iri"])
        for ftu in cell_types_in_ftu
        for ct in ftu.get("cell_types_in_ftu_only", [])
        if ftu["organ_id_short"] == organ_id_to_check
        and ct["representation_of"] == cell_id_to_check
    ]

    return matches


def iterate_through_json_lines(filename: str, print_line: bool = False):
    """Iterate through a JSON Lines (JSONL) file and yield each JSON object.

    This function reads a JSONL file line by line, parsing each line into a
    Python dictionary (or list, depending on the JSON content). It uses `tqdm`
    to display a progress bar and optionally prints each parsed object.

    Args:
        filename (str): Path to the JSONL file to read.
        print_line (bool, optional): If True, pretty-prints each parsed JSON object.
            Defaults to False.

    Yields:
        dict | list: The JSON object from each line of the file.

    Example:
        >>> for obj in iterate_through_json_lines('data.jsonl'):
        ...     print(obj['id'])
    """
    total_lines = sum(1 for _ in open(filename, "r", encoding="utf-8"))

    print(
        f"Now processing {filename} with {total_lines} lines and printing {'enabled' if print_line else 'not enabled'}."
    )

    with open(filename, "r", encoding="utf-8") as f:
        for line in tqdm(
            f, total=total_lines, desc="Processing JSONL lines", unit="line"
        ):
            line = line.strip()
            if not line:
                continue
            line_json = json.loads(line)
            if print_line:
                pprint(line_json)
            yield line_json


def unzip_to_folder(file_path: str, target_folder: str):
    """
    Unzip the file at the specified file_path into target_folder,
    but only if the folder is empty.

    Args:
        file_path (str): Path to the .zip (or other archive) file.
        target_folder (str): Path where the archive should be extracted.
    """
    target = Path(target_folder)

    # Exclude the archive itself when checking contents
    if target.exists() and any(
        p.is_file() and p.suffix != ".zip" and ".tsv" not in p.name
        for p in target.iterdir()
    ):
        print(f"Skipped: {target} already contains extracted files.")
        return

    # Otherwise, unzip
    shutil.unpack_archive(file_path, target)
    print(f"Unzipped {file_path} → {target}")
