from shared import *


def main():
    pprint(df_illustrations_mouth)
    df_illustrations_mouth["is_in_supertree"] = df_illustrations_mouth[
        "OntologyID"
    ].apply(lambda row: check_if_cell_id_in_df(row, df_supertree))
    pprint(df_illustrations_mouth)

    df_illustrations_mouth.to_csv(REPORTS_DIR / "missing_in_supertree.csv", index=False)


if __name__ == "__main__":
    main()
