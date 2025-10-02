# commonly used packages in this workflow
from pprint import pprint
import requests
import pandas as pd
from io import StringIO
import json
from pathlib import Path

# Make folder for shared data
OUTPUT_DIR = Path(__file__).parent.parent / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)  # create the folder if it doesn't exist

# Set up JSON file to capture data structures for FTUs and cell types
CELL_TYPES_IN_FTUS = OUTPUT_DIR / "cell-types-in-ftus.json"

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
        ValueError: If the response is not valid CSV.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx, 5xx)

        # Optional: check content type
        content_type = response.headers.get("Content-Type", "")
        if (
            "text/csv" not in content_type
            and "application/octet-stream" not in content_type
        ):
            raise ValueError(f"Unexpected Content-Type: {content_type}")

        # Parse CSV
        return pd.read_csv(StringIO(response.text))

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch CSV from {url}") from e
    except pd.errors.ParserError as e:
        raise ValueError(f"Failed to parse CSV from {url}") from e
