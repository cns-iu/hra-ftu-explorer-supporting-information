from shared import *

# Filters the anatomogram (EBI Single Cell Expression Atlas) cell type populations in
# anatomogram-data/ to FTU-exclusive cell types, exactly like 20-preprocess-hra-pop.py does for
# the HRApop universe. The anatomogram files share HRApop's cell-summary JSONL and dataset-metadata
# CSV formats, so 40 and 41 pick up the results via CELL_SUMMARY_SOURCES in shared.py.


def main():
    # Load list of dictionaries with cell types in FTUs
    with open(CELL_TYPES_IN_FTUS, "r", encoding="utf-8") as cell_types_f:
        cell_types_in_ftus = json.load(cell_types_f)

    metadata = pd.read_csv(ANATOMOGRAM_DATASET_METADATA_FILENAME)

    datasets_of_interest = identify_datasets_of_interest(
        cell_types_in_ftus, metadata, ANATOMOGRAM_DATASETS_OF_INTEREST
    )

    filter_cell_summaries(
        datasets_of_interest,
        cell_types_in_ftus,
        ANATOMOGRAM_CELL_SUMMARIES_FILENAME,
        ANATOMOGRAM_FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME,
        ANATOMOGRAM_FILTERED_DATASET_METADATA_FILENAME,
    )


if __name__ == "__main__":
    main()
