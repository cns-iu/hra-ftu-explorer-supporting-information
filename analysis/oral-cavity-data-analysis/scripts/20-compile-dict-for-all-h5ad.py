from shared import *

result_dict = {}
folder_path = Path(RAW_DATA_DIR)


def open_h5ad_file(id: str) -> tuple:
    adata = ad.read_h5ad(RAW_DATA_DIR / id, backed="r")
    if "celltype" in adata.obs.columns:
        df = pd.DataFrame(
            adata.obs[
                ["cell_type", "celltype", "cell_type_ontology_term_id"]
            ].value_counts()
        )
    else:
        df = pd.DataFrame(
            adata.obs[
                ["cell_type", "author_cell_type", "cell_type_ontology_term_id"]
            ].value_counts()
        )

    # value_counts() on categorical columns also lists every combination that never occurs, with count 0
    df = df[df["count"] > 0]

    return (df, id)


def add_to_dict(df: pd.DataFrame, dataset_id: str):
    as_dict = df.to_dict(orient="index")

    result_dict[dataset_id] = []
    # pprint(as_dict)

    for cell_types, counts in as_dict.items():
        print(cell_types, counts)
        to_add = {}

        to_add["cl_label"] = cell_types[0]
        to_add["author_label"] = cell_types[1]
        to_add["cl_id"] = cell_types[2]
        to_add["count"] = counts["count"]
        print("==============")
        print(f"Added {to_add}")
        print("==============")
        result_dict[dataset_id].append(to_add)

    # df_as_value = df.to_dict(orient="records")
    # pprint(df_as_value)


def main():
    for file in folder_path.iterdir():
        if file.is_file() and "h5ad" in file.name:
            print(f"================")
            print(f"Now opening {file.name}")
            print()
            data = open_h5ad_file(file.name)
            add_to_dict(*data)

    pprint(result_dict)
    save_to_json(result_dict)


if __name__ == "__main__":
    main()
