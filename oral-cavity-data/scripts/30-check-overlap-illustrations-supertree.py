from shared import *

mouth_id = "UBERON:0000165"


def main():
    df_crosswalk_mouth = (
        df_illustration[df_illustration["organ_id"] == mouth_id][
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

    # pprint(df_supertree)
    pprint(df_crosswalk_mouth)
    df_crosswalk_mouth["is_in_supertree"] = df_crosswalk_mouth["OntologyID"].apply(
        lambda row: check_if_cell_id_in_df(row, df_supertree)
    )
    pprint(df_crosswalk_mouth)

    df_crosswalk_mouth.to_csv(REPORTS_DIR / "missing_in_supertree.csv", index=False)


if __name__ == "__main__":
    main()
