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


def get_organ_from_dataset_metadata(dataset_id_to_check: str, metadata:pd.DataFrame) -> str | None:
    """
    Get the organ label for a given dataset ID from the metadata.

    Args:
        check_dataset_id (str): The dataset ID to look up.

    Returns:
        str | None: The corresponding organ label, or None if not found.
    """

    match = metadata.loc[metadata["dataset_id"] == dataset_id_to_check, "organ"]

    return match.iloc[0] if not match.empty else None


def filter_raw_data():
    """
    Stream and filter the massive gzipped JSONL HRApop Universe file (≈36 GB),
    keeping only datasets and cell type populations related to organs that
    have Functional Tissue Units (FTUs).

    Shows a live progress bar while processing.
    """

    # Create a dictionary to hold data from the run
    datasets_with_ftus = []

    # Load FTU reference (assuming it's reasonably sized — otherwise use ijson)
    with open(CELL_TYPES_IN_FTUS, "r", encoding="utf-8") as cell_types_f:
        cell_types_in_ftus = json.load(cell_types_f)

    # You should be able to determine which datasets you are targeting
    # before you the loop, the organ it corresponds to, and the cell
    # types you want to check for (in a set). Then when you go through
    # the file, you only need to check if the dataset_id is in a
    # dictionary you created and at least one cell type is in the
    # set associated with the organ the dataset is associated with.
    # Those should all be quick lookups rather than reading/iterating,
    # which should improve the speed quite a bit. Still gonna take a
    # while to get through the gz file, but probably < 1hr.

    # USE metadata.csv to get inventory of dataset IDs of interest
    # Pass cell-types-in-ftu.json as argument
    # maybe use regex?
    # not needed to save

    # In the future, use duckdb and https://duckdb.org/docs/stable/data/json/loading_json to read the JSON-lines file?

    # Load HRApop Universe metdata
    metadata = pd.read_csv(UNIVERSE_METADATA_FILENAME)

    # Stream through the gzipped JSONL file
    with gzip.open(UNIVERSE_10K_FILENAME, "rt", encoding="utf-8") as f, open(
        FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME, "w", encoding="utf-8"
    ) as intermediary_file:

        # ✅ tqdm with no total (dynamic progress)
        for line in tqdm(f, desc="Processing JSONL lines", unit="line"):
            if not line.strip():
                continue

            try:
                cell_summary = json.loads(line)
            except json.JSONDecodeError as e:
                tqdm.write(f"⚠️ Skipping invalid JSON line: {e}")
                continue

            dataset_id = cell_summary["cell_source"]
            organ_id = get_organ_from_dataset_metadata(dataset_id, metadata)
            organ_has_ftus = comes_from_organ_with_ftu(organ_id, cell_types_in_ftus)

            tqdm.write(
                f"Dataset {cell_summary['cell_source']} has organ {organ_id}, which has FTUs: {organ_has_ftus}"
            )

            if organ_has_ftus:
                keep_summaries = []
                for cell_type in cell_summary.get("summary", []):

                    tqdm.write(f"Now checking {cell_type['cell_id']}.")

                    if is_cell_type_exclusive_to_ftu(
                        cell_type.get("cell_id"), organ_id, cell_types_in_ftus
                    ):
                        keep_summaries.append(cell_type)
                        tqdm.write(f"{cell_type['cell_id']} is exclusive to FTU.")

                if keep_summaries:
                    tqdm.write(
                        f"Found at least one CT in dataset {dataset_id} that is exclusive to FTU."
                    )

                    keep_cell_type_population = {
                        k: v for k, v in cell_summary.items() if k != "summary"
                    }
                    keep_cell_type_population["summary"] = keep_summaries
                    intermediary_file.write(
                        json.dumps(keep_cell_type_population) + "\n"
                    )

                    # Add dataset to dict
                    # datasets_with_ftus.append(
                    #     {
                    #         "dataset_id": dataset_id,
                    #         "ftu": "",
                    #         "cell_type": cell_type
                    #     }
                    # )

    with open(FILTERED_DATASET_METADATA_FILENAME, "w") as f:
        json.dump(datasets_with_ftus, f, indent=4)  # indent=4 makes it pretty


def main():
    # Driver code

    download_data()
    filter_raw_data()


if __name__ == "__main__":
    main()
