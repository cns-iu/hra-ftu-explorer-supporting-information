from shared import *


def download_hra_pop_data_data():
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
        f"https://raw.githubusercontent.com/x-atlas-consortia/hra-pop/refs/heads/{hra_pop_branch}/input-data/{hra_pop_version}/sc-transcriptomics-dataset-metadata.csv",
        UNIVERSE_METADATA_FILENAME,
    )

    download_from_url(
        "https://zenodo.org/records/15786154/files/sc-transcriptomics-cell-summaries.top10k.jsonl.gz?download=1",
        UNIVERSE_10K_FILENAME,
    )


def main():
    # Driver code

    # Load list of dictionaries with cell types in FTUs
    with open(CELL_TYPES_IN_FTUS, "r", encoding="utf-8") as cell_types_f:
        cell_types_in_ftus = json.load(cell_types_f)

    # Load HRApop Universe metdata
    metadata = pd.read_csv(UNIVERSE_METADATA_FILENAME)

    # Get HRApop Universe data from GitHub
    download_hra_pop_data_data()

    # Identify datasets of interest before iterating through big ZIP file
    datasets_of_interest = identify_datasets_of_interest(
        cell_types_in_ftus, metadata, DATASETS_OF_INTEREST
    )

    # Filter raw data with datasets of interest in mind
    filter_cell_summaries(
        datasets_of_interest,
        cell_types_in_ftus,
        UNIVERSE_10K_FILENAME,
        FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME,
        FILTERED_DATASET_METADATA_FILENAME,
    )


if __name__ == "__main__":
    main()
