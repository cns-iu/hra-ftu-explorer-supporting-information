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


def get_organ_from_dataset_metadata(
    dataset_id_to_check: str, metadata: pd.DataFrame
) -> str | None:
    """
    Get the organ label for a given dataset ID from the metadata.

    Args:
        check_dataset_id (str): The dataset ID to look up.

    Returns:
        str | None: The corresponding organ label, or None if not found.
    """

    match = metadata.loc[metadata["dataset_id"] == dataset_id_to_check, "organ"]

    return match.iloc[0] if not match.empty else None


def identify_datasets_of_interest(
    cell_types_in_ftus: list, metadata: pd.DataFrame
) -> list:
    """_summary_"""

    result = []

    for dataset_id in metadata["dataset_id"].unique():
        organ_id = get_organ_from_dataset_metadata(dataset_id, metadata)
        organ_has_ftus = comes_from_organ_with_ftu(organ_id, cell_types_in_ftus)

        if organ_has_ftus:
            result.append({dataset_id: organ_id})

    return list(result)


def filter_raw_data(datasets_of_interest: list, cell_types_in_ftus: list):
    """
    Stream and filter the massive gzipped JSONL HRApop Universe file (≈36 GB),
    keeping only datasets and cell type populations related to organs that
    have Functional Tissue Units (FTUs).

    Shows a live progress bar while processing.
    """

    # Precompute a fast lookup index that maps (organ_id_short, cell_id) → [ftu_iris]
    # This should be built once and reused for all subsequent lookups
    # index = build_ftu_index(cell_types_in_ftus)

    # Create a dictionary to hold datasets and confirmed CTs in FTUs from the run
    datasets_with_ftus = {}

    # Perform list comprehension to create a list of unique dataset IDs of interest

    # Remove this and uncomment statement below once testing is done
    # unique_dataset_ids_of_interest = [
    #     "https://doi.org/10.1126/science.abl4290#GTEX-1HSMQ-5014-SM-GKSJI"
    # ]

    unique_dataset_ids_of_interest = set(
        [list(d.keys())[0] for d in datasets_of_interest]
    )

    # In the future, use duckdb and https://duckdb.org/docs/stable/data/json/loading_json to read the JSON-lines file?

    # Precompile one regex for all dataset IDs of interest
    pattern = re.compile("|".join(map(re.escape, unique_dataset_ids_of_interest)))

    # Numbers of characters to search in line before loading to JSON
    N = 500

    # Stream through the gzipped JSONL file
    with (
        gzip.open(UNIVERSE_10K_FILENAME, "rt", encoding="utf-8") as f,
        open(
            FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME,
            "w",
            encoding="utf-8",
        ) as intermediary_file,
    ):
        # tqdm with no total (dynamic progress)
        for line in tqdm(f, desc="Processing JSONL lines", unit="line"):
            # Guard clauses
            if not line.strip():
                continue
            # Quick text pre-filter — skips most lines cheaply
            if not pattern.search(line[:N]):
                continue  # no dataset ID → skip

            try:
                cell_summary = ujson.loads(line)
            except ujson.JSONDecodeError as e:
                tqdm.write(f"⚠️ Skipping invalid JSON line: {e}")
                continue

            current_dataset_id = cell_summary["cell_source"]

            if current_dataset_id in unique_dataset_ids_of_interest:
                # tqdm.write(
                #     f"Dataset {current_dataset_id} is of interest, now checking its cell types."
                # )
                keep_summaries = []

                for cell_type in cell_summary.get("summary", []):
                    organ_id = next(
                        (
                            v
                            for d in datasets_of_interest
                            for k, v in d.items()
                            if k == current_dataset_id
                        ),
                        "ORGAN NOT FOUND",  # default if not found
                    )

                    matches = is_cell_type_exclusive_to_ftu(
                        cell_type.get("cell_id"), organ_id, cell_types_in_ftus
                    )

                    if matches:
                        keep_summaries.append(cell_type)
                        tqdm.write(
                            f"{cell_type['cell_id']} is exclusive to FTU. Matches: "
                        )
                        tqdm.write(str(matches))

                        if current_dataset_id not in datasets_with_ftus:
                            datasets_with_ftus[current_dataset_id] = []
                        datasets_with_ftus[current_dataset_id].append(matches)

                if keep_summaries:
                    tqdm.write(
                        f"Found {len(datasets_with_ftus[current_dataset_id])} CT(s) in dataset {current_dataset_id} that is exclusive to FTU."
                    )

                    keep_cell_type_population = {
                        k: v for k, v in cell_summary.items() if k != "summary"
                    }
                    keep_cell_type_population["summary"] = keep_summaries

                    intermediary_file.write(
                        json.dumps(keep_cell_type_population) + "\n"
                    )

                    # tqdm.write(
                    #     f"Datasets with confirmed FTUs is now: {datasets_with_ftus}."
                    # )

    with open(FILTERED_DATASET_METADATA_FILENAME, "w") as f:
        json.dump(datasets_with_ftus, f, indent=4)  # indent=4 makes it pretty


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
    datasets_of_interest = identify_datasets_of_interest(cell_types_in_ftus, metadata)

    # Filter raw data with datasets of interest in mind
    filter_raw_data(datasets_of_interest, cell_types_in_ftus)


if __name__ == "__main__":
    main()
