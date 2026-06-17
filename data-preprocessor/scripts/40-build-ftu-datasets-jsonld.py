from shared import *


def build_ftu_datasets_jsonld(metadata: pd.DataFrame):
    """_summary_"""
    out_json_ld = copy.deepcopy(context_template)

    graph_list = []

    # Holds one list of sources per FTU
    ftu_instance = {
        "@id": "",  # PURL for the FTU
        "@type": "FtuIllustration",  # static
        "data_sources": [],  # list of papers --need to adjust for HRApop for the time being
    }

    data_source_instance = {
        "@id": "",  # Dataset ID
        "@type": "Dataset",  # static
        "label": "",
        "link": "",  # Dataset ID
        "description": "",
        "year": 0000,
        "authors": [],  # Creator(s)?
    }

    ftu_to_datasets = defaultdict(set)

    with open(FILTERED_DATASET_METADATA_FILENAME, "r") as f:
        data = json.load(f)

        for dataset_id, cts in data.items():
            for ct in cts:
                ftu = ct["ftu_purl"]
                ftu_to_datasets[ftu].add(dataset_id)

        # convert sets → lists
        ftu_to_datasets = {k: list(v) for k, v in ftu_to_datasets.items()}

    # save to file
    with open(FTU_TO_DATASETS, "w") as output:
        json.dump(ftu_to_datasets, output, indent=4)

    print()
    pprint(ftu_to_datasets)
    print()
    # return

    # Fast lookup: dataset_id -> metadata row
    metadata_by_dataset = metadata.set_index("dataset_id")[
        ["handler", "provider_name"]
    ].to_dict("index")

    # Invert: dataset_id -> [ftu1, ftu2, ...]
    dataset_to_ftus = defaultdict(list)
    for ftu, dataset_ids in ftu_to_datasets.items():
        for dataset_id in dataset_ids:
            dataset_to_ftus[dataset_id].append(ftu)

    # Collect which dataset_ids belong to which FTU in one pass
    ftu_to_dataset_ids = defaultdict(set)

    for obj in iterate_through_json_lines(
        FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME
    ):
        dataset_id = obj["cell_source"]
        for ftu in dataset_to_ftus.get(dataset_id, ()):
            ftu_to_dataset_ids[ftu].add(dataset_id)

    graph_list = []

    for ftu in ftu_to_datasets:
        new_ftu = deepcopy(ftu_instance)
        new_ftu["@id"] = ftu
        new_ftu["data_sources"] = []

        suffix = ftu.rsplit("/", 1)[-1]

        for dataset_id in ftu_to_dataset_ids.get(ftu, ()):
            md = metadata_by_dataset.get(dataset_id)
            if md is None:
                continue

            new_data_source = deepcopy(data_source_instance)
            new_data_source["@id"] = f"{dataset_id}#CellSummary_{suffix}"
            new_data_source["label"] = md["handler"]
            new_data_source["link"] = dataset_id
            new_data_source["description"] = dataset_id
            new_data_source["authors"] = [md["provider_name"]]

            new_ftu["data_sources"].append(new_data_source)

        graph_list.append(new_ftu)

    out_json_ld["@graph"] = graph_list

    # Write to file
    print(f"Now saving to {FTU_DATASETS_OUTPUT}")
    with open(FTU_DATASETS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out_json_ld, f, ensure_ascii=False, indent=4)


def main():
    # Driver code

    metadata = pd.read_csv(UNIVERSE_METADATA_FILENAME).reset_index(drop=True)

    build_ftu_datasets_jsonld(metadata=metadata)


if __name__ == "__main__":
    main()
