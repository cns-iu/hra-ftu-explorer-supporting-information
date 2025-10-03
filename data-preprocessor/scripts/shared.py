# commonly used packages in this workflow
from pprint import pprint
import yaml
import requests
import pandas as pd
from io import StringIO
import json
from pathlib import Path
import gzip

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
RAW_DATA_DIR = Path(__file__).parent.parent / "raw-data" # for files larger than 100 MB, move HRApop data here as needed
RAW_DATA_DIR.mkdir(exist_ok=True)  # create the folder if it doesn't exist

# Capture script folder
SCRIPT_DIR = Path(__file__).parent


# Assign file paths to constants
with open(Path(__file__).parent / "config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

CELL_TYPES_IN_FTUS = OUTPUT_DIR / config["CELL_TYPES_IN_FTUS"]
UNIVERSE_FILE_FILENAME = INPUT_DIR / config["UNIVERSE_FILE_FILENAME"]
UNIVERSE_METADATA_FILENAME = INPUT_DIR / config["UNIVERSE_METADATA_FILENAME"]
ATLAS_FILE_FILENAME = INPUT_DIR / config["ATLAS_FILE_FILENAME"]

# Commonly used HTTP Accept headers for API requests
accept_json = {"Accept": "application/json"}
accept_csv = {"Accept": "text/csv"}


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


def download_from_url(url: str, output_file: str):
    """
    Download a gzipped JSONL file or a CSV and save it locally,
    but only if it does not already exist.

    This function streams the file from the provided URL in chunks to avoid loading
    the entire file into memory, and writes it to the specified output location
    inside the configured INPUT_DIR.

    Args:
        url (str): The URL of the file to download.
        output_file (str): The filename to save the downloaded file as (relative to INPUT_DIR).

    Side effects:
        - Saves the file to disk at INPUT_DIR/output_file if it does not exist yet.
        - Prints a confirmation message if the file is downloaded or already exists.

    Raises:
        HTTPError: If the HTTP request for the URL fails.
        OSError: If writing to the local file path fails.
    """
    file_path = Path(INPUT_DIR) / output_file

    if file_path.exists():
        print(f"ℹ️ File already exists at {file_path}, skipping download.")
        return file_path

    # stream download to avoid loading whole file in memory
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

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


def comes_from_organ_with_ftu(check_organ_id: str) -> bool:
    """
    Check whether a given organ ID corresponds to an organ that has FTUs (Functional Tissue Units).

    Args:
        check_organ_id (str): The short organ ID to check.

    Returns:
        bool: True if the organ has FTUs, False otherwise.
    """
    # Load cell types in FTUs
    with open(CELL_TYPES_IN_FTUS, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"✅ Loaded {CELL_TYPES_IN_FTUS}")

    return check_organ_id in {ftu["organ_id_short"] for ftu in data}
