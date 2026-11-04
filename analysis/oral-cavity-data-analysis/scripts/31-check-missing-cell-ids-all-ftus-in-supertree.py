from shared import *


def main():

    # A new name, not df_illustrations: assigning to that would make it local to main() for the whole function
    df_crosswalk = (
        df_illustrations[
            [
                "organ_label",
                "organ_id",
                "anatomical_structure_of",
                "label",
                "OntologyID",
            ]
        ]
        .drop_duplicates()
        .dropna()
    )
    df_crosswalk["is_in_supertree"] = df_crosswalk["OntologyID"].apply(
        lambda row: check_if_cell_id_in_df(row, df_supertree)
    )
    df_crosswalk = df_crosswalk[~df_crosswalk["OntologyID"].str.contains("UBERON")]

    df_crosswalk.to_csv(REPORTS_DIR / "missing_in_supertree-all-ftus.csv", index=False)

    print(f"Saved report to {REPORTS_DIR / "missing_in_supertree-all-ftus.csv"}")


if __name__ == "__main__":
    main()
