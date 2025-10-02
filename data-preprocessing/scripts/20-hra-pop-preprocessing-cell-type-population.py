from shared import *

# Set file names
UNIVERSE_FILE_FILENAME = "sc-transcriptomics-cell-summaries.jsonl.gz"
UNIVERSE_METADATA_FILENAME = "sc-transcriptomics-dataset-metadata.csv"
ATLAS_FILE_FILENAME = "atlas-enriched-dataset-graph.jsonld"


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

    # Download Atlas data
    download_from_url(
        "https://cdn.humanatlas.io/digital-objects/graph/hra-pop/v1.0/assets/atlas-enriched-dataset-graph.jsonld",
        ATLAS_FILE_FILENAME,
    )


def filter_cell_type_populations():
    """_summary_"""
    
    # Load cell type populations for Universe datasets
    

    # atlas = open_cell_type_populations(f"{INPUT_DIR}/{ATLAS_FILE_NAME}")
    # for donor in atlas["@graph"]:
    #     print(donor['@id'])

    # load cell types in FTUs
    # with open(CELL_TYPES_IN_FTUS) as f:
    #     data = json.load(f)
    #     print(f"✅ Loaded {CELL_TYPES_IN_FTUS}")


def main():
    # Driver code

    download_data()


if __name__ == "__main__":
    main()
