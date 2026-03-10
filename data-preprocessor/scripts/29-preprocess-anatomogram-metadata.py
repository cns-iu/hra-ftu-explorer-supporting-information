from shared import *


def extract_metadata(organ_metadata: dict):
    """_summary_"""

    # Load metadata TSV
    print()
    print(f"Getting metadata for {organ_metadata['name']}:")
    df = pd.read_csv(
        ANATOMOGRAMN_RAW_DATA
        / organ_metadata["name"]
        / f"{organ_metadata['experiment_id']}.tsv",
        sep="\t",
    )
    pprint(df)

    # Rename columns
    column_mapping = {
        "Assay": "assay",
        "Sample Characteristic[organism]": "organism",
        "Sample Characteristic[individual]": "donor",
        "Sample Characteristic[organism part]": "as_label",
        "Sample Characteristic Ontology Term[organism part]": "as_id",
        "Sample Characteristic[sex]": "sex",
        "Sample Characteristic[ethnic group]": "ethnicity",
        "Sample Characteristic[age]": "age",
        "Sample Characteristic[body mass index]": "bmi",
        "Sample Characteristic[disease]": "disease",
        "Factor Value Ontology Term[inferred cell type - ontology labels]": "cell_id",
        "Factor Value[inferred cell type - ontology labels]": "cell_type",
    }

    df = df.rename(columns=column_mapping)

    print("Experimental design file:")
    pprint(df)
    print()
    unique_count = df[["donor", "sex", "age", "as_label"]].drop_duplicates().shape[0]
    print(f"Number of unique donors: {unique_count}")
    print()
    df_unique_donors = df[["donor", "sex", "age", "as_label"]].drop_duplicates()
    print("Unique donors:")
    pprint(df_unique_donors)
    print()

    df["dataset_id"] = (
        organ_metadata["paper_doi"]
        + "#"
        + df["donor"].astype(str)
        + "$"
        + df["as_label"].str.replace(" ", "-")
    )

    print("Unique dataset IDs:")
    pprint(df["dataset_id"].unique())

    # Prepare export
    export = {
        "id": df["dataset_id"],
        "handler": "anatomogram",
        "organ": organ_metadata["organ_id"],
        "dataset_id": df["dataset_id"],
        "dataset_link": organ_metadata["dataset_link"],
        "publication": organ_metadata["paper_doi"],
    }

    # Only keep rows unique dataset IDs
    export_df = pd.DataFrame(export).drop_duplicates(subset="dataset_id", keep="first")

    # Append to file (no header)
    with open(ANATOMOGRAMN_METADATA, "a", encoding="utf-8", newline="") as f:
        export_df.to_csv(f, header=False, index=False)


def main():
    # Driver code
    print("Now making metadata file for anatomogram.")

    for organ in anatomogram_files_json:
        extract_metadata(organ)


if __name__ == "__main__":
    main()
