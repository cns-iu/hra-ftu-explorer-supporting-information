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


def build_dataset_metadata_jsonld(metadata: pd.DataFrame):
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

    look_up_ftu_to_datasets = {}

    with open(FILTERED_DATASET_METADATA_FILENAME, 'r') as f:
        data = json.load(f)

        look_up_ftu_to_datasets = defaultdict(list)

        for dataset, groups in data.items():
            for group in groups:
                for _, purl in group:
                    if dataset not in look_up_ftu_to_datasets[purl]:
                        look_up_ftu_to_datasets[purl].append(dataset)

    print()
    pprint(look_up_ftu_to_datasets)
    print()

    for ftu in look_up_ftu_to_datasets:
        print(ftu)

        new_ftu = copy.deepcopy(ftu_instance)

        # Fill fields in @graph
        new_ftu["@id"] = ftu  # hard-coded for now since all datasets with FTUs are from prostate

        for obj in iterate_through_json_lines(
            FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME
        ):
            dataset_id = obj["cell_source"]

            # get right dataset ID
            for ftu in look_up_ftu_to_datasets: 
                if dataset_id in look_up_ftu_to_datasets[ftu]:

                    # Get metadata
                    metadata_instance = metadata[metadata["dataset_id"] == dataset_id]

                    new_data_source = copy.deepcopy(data_source_instance)

                    new_data_source["@id"] = dataset_id + "#CellSummary_" + new_ftu["@id"].split("/")[-1]
                    new_data_source["label"] = metadata_instance.iloc[0]["handler"]
                    new_data_source["link"] = dataset_id
                    new_data_source["description"] = dataset_id
                    new_data_source["authors"] = [
                        metadata_instance.iloc[0]["provider_name"]
                    ]

                    new_ftu["data_sources"].append(new_data_source)

        graph_list.append(new_ftu)

    out_json_ld["@graph"] = graph_list

    # Write to file
    print(f"Now saving to {FTU_DATASETS_OUTPUT}")
    with open(FTU_DATASETS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out_json_ld, f, ensure_ascii=False, indent=4)


def build_cell_summaries_jsonld():
    """_summary_"""

    # turn into JSONLD files with context
    out_json_ld = copy.deepcopy(context_template)

    for obj in iterate_through_json_lines(
        FILTERED_FTU_CELL_TYPE_POPULATIONS_INTERMEDIARY_FILENAME
    ):
        # Enrich with needed fields
        obj["cell_source"] = (
            obj["cell_source"]
            + "#CellSummary_"
            + "https://purl.humanatlas.io/2d-ftu/prostate-prostate-glandular-acinus".split(
                "/"
            )[
                -1
            ]
        )
        obj["annotation_method"] = "Aggregation"
        obj["biomarker_type"] = "gene"
        obj.pop("modality")

        for summary in obj["summary"]:
            summary["@type"] = "CellSummaryRow"
            summary["genes"] = summary.pop("gene_expr")
            summary["cell_id"] = "http://purl.obolibrary.org/obo/" + summary[
                "cell_id"
            ].replace(":", "_")

            for gene in summary["genes"]:
                gene["@type"] = "GeneExpression"
                gene["ensemble_id"] = gene.pop("ensembl_id")
                gene["mean_expression"] = gene.pop("mean_gene_expr_value")

        out_json_ld["@graph"].append(obj)

    # Write to file
    print(f"Now saving to {FTU_CELL_SUMMARIES_OUTPUT}")
    with open(FTU_CELL_SUMMARIES_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out_json_ld, f, ensure_ascii=False, indent=4)


def main():
    # Driver code

    metadata = pd.read_csv(UNIVERSE_METADATA_FILENAME).reset_index(drop=True)

    build_dataset_metadata_jsonld(metadata=metadata)
    build_cell_summaries_jsonld()


if __name__ == "__main__":
    main()
