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
    """
    Stream and filter the massive gzipped JSONL HRApop Universe file (≈36 GB),
    keeping only datasets and cell type populations related to organs that
    have Functional Tissue Units (FTUs).

    Shows a live progress bar while processing.
    """
    ftu_datasets_raw = []
    ftu_cell_summaries_raw = []

    # Load FTU reference (assuming it's reasonably sized — otherwise use ijson)
    with open(CELL_TYPES_IN_FTUS, "r", encoding="utf-8") as cell_types_f:
        cell_types_in_ftus = json.load(cell_types_f)

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
            organ_id = get_organ_from_dataset_metadata(dataset_id)
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
