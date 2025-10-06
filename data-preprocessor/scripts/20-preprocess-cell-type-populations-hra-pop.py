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


def get_organ_from_dataset_metadata(dataset_id_to_check: str) -> str | None:
    """
    Get the organ label for a given dataset ID from the metadata.

    Args:
        check_dataset_id (str): The dataset ID to look up.

    Returns:
        str | None: The corresponding organ label, or None if not found.
    """

    metadata = pd.read_csv(UNIVERSE_METADATA_FILENAME)
    match = metadata.loc[metadata["dataset_id"] == dataset_id_to_check, "organ"]

    return match.iloc[0] if not match.empty else None


def filter_raw_data():
    """_summary_"""

    # First, we need to check if any cell type population has is from an organ that has an FTU
    # If yes, we need to check if any cell type population contains cell types only found in any FTUs for that organ

    # initialize lists to capture the raw data for display in the FTU Explorer
    ftu_datasets_raw = []
    ftu_cell_summaries_raw = []

    with open(CELL_TYPES_IN_FTUS, "r", encoding="utf-8") as cell_types_f:
        cell_types_in_ftus = json.load(cell_types_f)

    # Make intermediary file to hold cell type populations (ONLY CTs in FTUs) for datasets form organs with FTU
    # Load HRApop Universe cell type populations and filter out all that are not from FTU organs
    with open(
        FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME, "w", encoding="utf-8"
    ) as intermediary_file, gzip.open(
        UNIVERSE_10K_FILENAME, "rt", encoding="utf-8"
    ) as f:
        # total_lines = sum(1 for _ in f)
        for line in f:
            if line.strip():
                # load cell type population
                cell_summary = json.loads(line)

                # First check: Get dataset ID and check if it comes form an organ with FTUs
                dataset_id = cell_summary["cell_source"]
                organ_id = get_organ_from_dataset_metadata(dataset_id)
                organ_has_ftus = comes_from_organ_with_ftu(organ_id, cell_types_in_ftus)

                # Print result
                print()
                print(
                    f"Dataset {cell_summary['cell_source']} has organ {organ_id}, which has FTUs: {organ_has_ftus}"
                )

                # Second check: Get the cell types found exclusiveely within the FTU, then keep the populations for these cell types in a JSONL file (to be exported later for use in)
                if organ_has_ftus:

                    # Make empty list to hold what we need to keep
                    keep_summaries = []

                    # Check if cell type for dataset is unique to FTU. If yes, grab it.
                    for cell_type in cell_summary["summary"]:

                        print(f"Now checking {cell_type['cell_id']}.")

                        if is_cell_type_exclusive_to_ftu(
                            cell_type["cell_id"], organ_id, cell_types_in_ftus
                        ):
                            print()
                            pprint(f"{cell_type['cell_id']} is exclusive to FTU.")
                            print()
                            print(f"Keeping cell type population for {cell_type['cell_id']}")
                            keep_summaries.append(cell_type)

                    # If there are suitable cell types, add the cell type population with only that and other potential CTs to the intermediary file
                    if keep_summaries:

                        print(f"Found at least one CT in dataset {dataset_id} that is exclusive to FTU.")

                        # Make new dict to hold data and add summaries to keep
                        keep_cell_type_population = {
                            k: v for k, v in cell_summary.items() if k != "summary"
                        }

                        # Replace summary with what we need to keep
                        keep_cell_type_population["summary"] = keep_summaries

                        pprint(keep_cell_type_population)

                        # Write one JSON object per line
                        intermediary_file.write(
                            json.dumps(keep_cell_type_population) + "\n"
                        )


def build_jsonld_from_preprocessed():
    """_summary_"""

    # turn into JSONLD files with context


def main():
    # Driver code

    download_data()
    filter_raw_data()
    build_jsonld_from_preprocessed()

    # with gzip.open(UNIVERSE_10K_FILENAME, "rt", encoding="utf-8") as f:
    #     # total_lines = sum(1 for _ in f)
    #     for line in f:
    #         if line.strip():
    #             cell_summary = json.loads(line)
    #             pprint(cell_summary.keys())


if __name__ == "__main__":
    main()
