from shared import *


def download_data():
    """
    Download and load the sc-transcriptomics cell summaries dataset.

    This function:
      - Downloads the gzipped JSONL file of cell type populations from the HRA-pop repository.
      - Saves the file locally to the configured INPUT_DIR if not already there.

    Side effects:
        - Saves the downloaded file to INPUT_DIR.
    """

    # Download Universe metadata
    download_from_url(
        "https://github.com/x-atlas-consortia/hra-pop/raw/refs/heads/main/input-data/v1.0/sc-transcriptomics-cell-summaries.jsonl.gz",
        UNIVERSE_FILE_FILENAME,
    )

    download_from_url(
        "https://raw.githubusercontent.com/x-atlas-consortia/hra-pop/refs/heads/main/input-data/v1.0/sc-transcriptomics-dataset-metadata.csv",
        UNIVERSE_METADATA_FILENAME,
    )

    # Download Universe metadata with 10k cells from Zenodo
    # THEN MOVE TO RAW-DATA, make local file for input?
    # For gzip 36 GB, create an intermediate file, save locally.

    download_from_url(
        "https://zenodo.org/records/15786154/files/sc-transcriptomics-cell-summaries.top10k.jsonl.gz?download=1",
        UNIVERSE_10K_FILENAME,
    )

    # Download Atlas data
    download_from_url(
        "https://cdn.humanatlas.io/digital-objects/graph/hra-pop/v1.0/assets/atlas-enriched-dataset-graph.jsonld",
        ATLAS_FILE_FILENAME,
    )


def get_organ_from_metadata(check_dataset_id: str) -> str | None:
    """
    Get the organ label for a given dataset ID from the metadata.

    Args:
        check_dataset_id (str): The dataset ID to look up.

    Returns:
        str | None: The corresponding organ label, or None if not found.
    """
    metadata = pd.read_csv(UNIVERSE_METADATA_FILENAME)
    match = metadata.loc[metadata["dataset_id"] == check_dataset_id, "organ"]

    return match.iloc[0] if not match.empty else None


def preprocess_10k_data():
    """_summary_"""
    
    with gzip.open(UNIVERSE_10K_FILENAME, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cell_summary = json.loads(line)
                print(cell_summary["cell_source"])
                # discard if not from an organ with FTU
                # pprint(cell_summary['summary'])
                # do something with obj here
    
    


def filter_cell_type_populations():
    """_summary_"""

    # First, we need to check if any cell type population has is from an organ that has an FTU
    # If yes, we need to check if any cell type population contains cell types only found in any FTUs for that organ

    print(comes_from_organ_with_ftu("UBERON:0002370"))
    print(
        get_organ_from_metadata(
            "https://entity.api.hubmapconsortium.org/entities/9457860c1b69f7ec3e51a6b648eabf13"
        )
    )

    # Load HRApop Universe cell type populations and filter out all that are not from FTU organs

    with gzip.open(UNIVERSE_FILE_FILENAME, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cell_summary = json.loads(line)
                # print(cell_summary["cell_source"])
                # discard if not from an organ with FTU
                # pprint(cell_summary['summary'])
                # do something with obj here


def main():
    # Driver code

    download_data()
    preprocess_10k_data()
    filter_cell_type_populations()


if __name__ == "__main__":
    main()
