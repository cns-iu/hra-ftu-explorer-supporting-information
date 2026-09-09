from shared import *
import pandas as pd


def load_ftu_query_and_count():
    # Load CTs per FTU illustration
    ftu_query_result = pd.read_csv(FTU_QUERY)
    pprint(ftu_query_result)

    ct_counts_in_ftu_illustrations = (
    ftu_query_result.groupby("ftu_label")[["ct_iri"]]
    .nunique()
    .reset_index()
)

    # extra column: unique count of col_x, restricted to rows where coldhwuhduw is True
    filtered_counts = (
        ftu_query_result[ftu_query_result["exclusive_ct_in_ftu"] == True]
        .groupby("ftu_label")["ct_iri"]
        .nunique()
        .rename("ct_iri_true_count")
    )

    ct_counts_in_ftu_illustrations = ct_counts_in_ftu_illustrations.merge(filtered_counts, on="ftu_label", how="left")
    ct_counts_in_ftu_illustrations["ct_iri_true_count"] = ct_counts_in_ftu_illustrations["ct_iri_true_count"].fillna(0).astype(int)
    pprint(ct_counts_in_ftu_illustrations)
    
    return ct_counts_in_ftu_illustrations

def load_universe_cell_summaries():
    for obj in iterate_through_json_lines(UNIVERSE_10K_FILENAME):
        pprint(obj.keys())

def main():
    ct_counts_in_ftu_illustrations = load_ftu_query_and_count()

    # Save result
    save_df(ct_counts_in_ftu_illustrations, "cell_types_and_datasets_per_ftu.csv")

    load_universe_cell_summaries()

if __name__ == "__main__":
    main()
