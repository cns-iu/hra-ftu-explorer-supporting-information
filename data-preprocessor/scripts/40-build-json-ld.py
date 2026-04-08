from shared import *

# Boilerplate context and graph for JSON-LD file

context_template = {
    "@context": [
        "https://cns-iu.github.io/hra-cell-type-populations-supporting-information/data-processor/ccf-context.jsonld",
        {
            "UBERON": {
                "@id": "http://purl.obolibrary.org/obo/UBERON_",
                "@prefix": True,
            },
            "illustration_files": {
                "@id": "ccf:has_illustration_file",
                "@type": "@id",
            },
            "mapping": {"@id": "ccf:has_illustration_node", "@type": "@id"},
            "organ_id": {"@id": "ccf:organ_id", "@type": "@id"},
            "data_sources": {"@id": "ccf:has_data_source", "@type": "@id"},
        },
    ],
    "@graph": [],
}


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


def build_ftu_cell_summaries_jsonld():
    """_summary_"""

    # turn into JSONLD files with context
    out_json_ld = copy.deepcopy(context_template)

    with open(FTU_TO_DATASETS, "r", encoding="utf-8") as f:
        ftu_to_datasets = json.load(f)


    obj_counter = 0
    for obj in iterate_through_json_lines(
        FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME
    ):
        if obj_counter > 3:
            break
        else:
            obj_counter = obj_counter + 1
            # Enrich with needed fields
            cell_source = obj["cell_source"]

            # Find FTU for dataset
            for ftu in ftu_to_datasets:
                if cell_source in ftu_to_datasets[ftu]:
                    tqdm.write(f"Found {cell_source} in {ftu}")
                    dataset_id = cell_source
                    suffix = ftu.rsplit("/", 1)[-1]
                    tqdm.write(f"suffix: {suffix}")
                    cell_source = f"{dataset_id}#CellSummary_{suffix}"

            obj["cell_source"] = cell_source
            tqdm.write("")
            tqdm.write(f"Now making summary for {cell_source}")
            tqdm.write("")

            obj["annotation_method"] = "Aggregation"
            obj["biomarker_type"] = "gene"
            obj.pop("modality")

            for summary in obj["summary"]:
                summary["@type"] = "CellSummaryRow"
                summary["genes"] = summary.pop("gene_expr")
                summary["cell_id"] = "http://purl.obolibrary.org/obo/" + summary[
                    "cell_id"
                ].replace(":", "_")
                summary["cell_label"] = summary["cell_label"].lower()
                
                gene_counter = 0
                keep_genes = []
                for gene in summary["genes"]:
                    if gene_counter > 10:
                        break
                    else:
                        gene_counter = gene_counter + 1
                        keep_genes.append(gene)
                        try:
                            gene["@type"] = "GeneExpression"
                            gene["ensemble_id"] = gene.pop(
                                "ensembl_id"
                            )  # this is in the target format but a wrong spelling! https://github.com/hubmapconsortium/hra-ui/blob/8c5504291da52c2b3d8b0a5c410e21b84acd4d83/apps/ftu-ui/public/assets/TEMP/ftu-cell-summaries.jsonld#L41
                            gene["mean_expression"] = gene.pop("mean_gene_expr_value")
                        except:
                            if not isinstance(gene, dict):
                                tqdm.write(
                                    f"Expected gene dict, got {type(gene)}: {gene} with {len(gene)} entries."
                                )
                            # pass
                summary["genes"] = keep_genes

            tqdm.write(
                f"Done making cell summary for {cell_source} with len = {len(summary)}."
            )
            tqdm.write("======================")
            tqdm.write("")

            out_json_ld["@graph"].append(obj)
            # break

    # Write to file
    tqdm.write(f"Now saving to {FTU_CELL_SUMMARIES_OUTPUT}")
    with open(FTU_CELL_SUMMARIES_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out_json_ld, f, ensure_ascii=False, indent=4)


def main():
    # Driver code

    metadata = pd.read_csv(UNIVERSE_METADATA_FILENAME).reset_index(drop=True)

    build_ftu_datasets_jsonld(metadata=metadata)
    build_ftu_cell_summaries_jsonld()


if __name__ == "__main__":
    main()
