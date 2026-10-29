from shared import *

# Filters the oral cavity (CellxGene Human Oral and Craniofacial Cell Atlas) cell type populations in
# oral-cavity-data/ to FTU-exclusive cell types, like 25-preprocess-anatomogram.py. The files share HRApop's
# cell-summary JSONL and dataset-metadata CSV formats, so 40 and 41 pick up the results via CELL_SUMMARY_SOURCES.
#
# Unlike HRApop and the anatomogram, these datasets are tagged with the tissue they come from (e.g., parotid
# gland) instead of the organ (mouth). The mouth's FTUs (salivary glands) share almost all of their exclusive cell
# types, so matching by organ would put every dataset into every gland. Instead, each dataset goes only into the
# FTU of its own tissue (ORAL_CAVITY_TISSUE_TO_FTU in config.yaml), and datasets from other tissues are left out.


def get_organ_of_ftu(ftu_purl: str, cell_types_in_ftus: dict) -> str:
    return next(
        ftu["organ_id_short"]
        for ftu in cell_types_in_ftus.values()
        if ftu["ftu_purl"] == ftu_purl
    )


def main():
    # Load list of dictionaries with cell types in FTUs
    with open(CELL_TYPES_IN_FTUS, "r", encoding="utf-8") as cell_types_f:
        cell_types_in_ftus = json.load(cell_types_f)

    metadata = pd.read_csv(ORAL_CAVITY_DATASET_METADATA_FILENAME)

    # Keep only datasets from a tissue that is an FTU, and give them their FTU's organ (mouth) so the shared
    # filter below treats them like any other dataset from an organ with FTUs
    metadata = metadata[metadata["organ"].isin(ORAL_CAVITY_TISSUE_TO_FTU)].copy()
    ftu_by_dataset = dict(
        zip(metadata["dataset_id"], metadata["organ"].map(ORAL_CAVITY_TISSUE_TO_FTU))
    )
    metadata["organ"] = metadata["organ"].map(
        lambda tissue: get_organ_of_ftu(
            ORAL_CAVITY_TISSUE_TO_FTU[tissue], cell_types_in_ftus
        )
    )

    datasets_of_interest = identify_datasets_of_interest(
        cell_types_in_ftus, metadata, ORAL_CAVITY_DATASETS_OF_INTEREST
    )

    filter_cell_summaries(
        datasets_of_interest,
        cell_types_in_ftus,
        ORAL_CAVITY_CELL_SUMMARIES_FILENAME,
        ORAL_CAVITY_FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME,
        ORAL_CAVITY_FILTERED_DATASET_METADATA_FILENAME,
    )

    # filter_cell_summaries matches a dataset to every mouth FTU; keep only its own tissue's FTU. 40 assigns
    # datasets to FTUs from these matches, and 41 only writes the FTUs 40 assigned, so the intermediary can keep
    # CTs of other glands.
    with open(ORAL_CAVITY_FILTERED_DATASET_METADATA_FILENAME, "r", encoding="utf-8") as f:
        matches_by_dataset = json.load(f)
    matches_by_dataset = {
        dataset_id: kept
        for dataset_id, matches in matches_by_dataset.items()
        if (
            kept := [m for m in matches if m["ftu_purl"] == ftu_by_dataset[dataset_id]]
        )
    }
    with open(ORAL_CAVITY_FILTERED_DATASET_METADATA_FILENAME, "w", encoding="utf-8") as f:
        json.dump(matches_by_dataset, f, indent=4)

    print(
        f"{len(matches_by_dataset)} oral cavity dataset(s) have CTs exclusive to their tissue's FTU"
    )


if __name__ == "__main__":
    main()
