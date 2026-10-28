import json
from pathlib import Path

import requests

from shared import *

# CellxGene "Human Oral and Craniofacial Cell Atlas"
COLLECTION_ID = "065ad318-59fd-4f8c-b4b1-66caa7665409"
COLLECTION_API_URL = (
    f"https://api.cellxgene.cziscience.com/curation/v1/collections/{COLLECTION_ID}"
)

CHUNK_SIZE = 8 * 1024 * 1024


def get_collection():
    """Get the collection's metadata, incl. each dataset's H5AD URL, from the CellxGene Curation API."""
    response = requests.get(COLLECTION_API_URL, timeout=60)
    response.raise_for_status()
    return response.json()


def download_file(url: str, out_path: Path, expected_size: int):
    """Stream url to out_path, resuming from out_path.part if a previous download was interrupted."""
    if out_path.exists() and out_path.stat().st_size == expected_size:
        print(f"  already downloaded: {out_path.name}")
        return

    part_path = out_path.with_suffix(out_path.suffix + ".part")
    downloaded = part_path.stat().st_size if part_path.exists() else 0
    headers = {"Range": f"bytes={downloaded}-"} if downloaded else {}

    with requests.get(url, headers=headers, stream=True, timeout=60) as response:
        response.raise_for_status()
        if downloaded and response.status_code != 206:
            # Server ignored the Range header, start over
            downloaded = 0
        with open(part_path, "ab" if downloaded else "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
                downloaded += len(chunk)
                print(
                    f"\r  {downloaded / 1e6:,.0f} / {expected_size / 1e6:,.0f} MB",
                    end="",
                    flush=True,
                )
    print()

    if downloaded != expected_size:
        raise RuntimeError(
            f"{out_path.name}: got {downloaded} bytes, expected {expected_size}"
        )
    part_path.replace(out_path)


def download_h5ad_files():
    """Download every H5AD in the collection to raw-data/<dataset_id>.h5ad, plus collection.json."""
    collection = get_collection()
    with open(RAW_DATA_DIR / "collection.json", "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2)

    datasets = collection["datasets"]
    print(
        f"{collection['name']} (DOI {collection.get('doi')}): {len(datasets)} datasets"
    )

    for i, dataset in enumerate(datasets, 1):
        h5ad = next(a for a in dataset["assets"] if a["filetype"] == "H5AD")
        print(
            f"[{i}/{len(datasets)}] {dataset['title']} ({dataset['cell_count']:,} cells)"
        )
        download_file(
            h5ad["url"],
            RAW_DATA_DIR / f"{dataset['dataset_id']}.h5ad",
            h5ad["filesize"],
        )

    return collection


def main():
    download_h5ad_files()


if __name__ == "__main__":
    main()
