from shared import *


def build_ftu_cell_summaries_jsonld():
    """_summary_"""

    # turn into JSONLD files with context
    out_json_ld = copy.deepcopy(context_template)

    with open(FTU_TO_DATASETS, "r", encoding="utf-8") as f:
        ftu_to_datasets = json.load(f)

    exclusive_cts_by_ftu = load_exclusive_cts_by_ftu()

    dataset_to_ftus = defaultdict(set)
    for ftu_purl, dataset_ids in ftu_to_datasets.items():
        for dataset_id in dataset_ids:
            dataset_to_ftus[dataset_id].add(ftu_purl)

    obj_counter = 0
    for obj in iterate_preferred_cell_summaries():
        obj_counter += 1
        dataset_id = obj.get("cell_source")
        candidate_ftus = dataset_to_ftus.get(dataset_id, set())

        for ftu in candidate_ftus:
            suffix = ftu.rsplit("/", 1)[-1]
            cell_source = f"{dataset_id}#CellSummary_{suffix}"
            allowed_cts = exclusive_cts_by_ftu.get(ftu, set())

            tqdm.write("")
            tqdm.write(f"Now working on cell_source #{obj_counter}: {cell_source}")
            tqdm.write("")

            keep_summary = []
            for summary in obj.get("summary", []):
                try:
                    cell_id_curie = get_id_from_iri(summary.get("cell_id"))
                    if not cell_id_curie or cell_id_curie not in allowed_cts:
                        continue

                    transformed_summary = copy.deepcopy(summary)
                    transformed_summary["@type"] = "CellSummaryRow"
                    transformed_summary["genes"] = transformed_summary.pop("gene_expr", [])
                    transformed_summary["cell_id"] = (
                        "http://purl.obolibrary.org/obo/"
                        + cell_id_curie.replace(":", "_")
                    )
                    transformed_summary["cell_label"] = transformed_summary[
                        "cell_label"
                    ].lower()

                    gene_counter = 0
                    keep_genes = []
                    for gene in transformed_summary["genes"]:
                        if gene_counter > 10:
                            break

                        gene_counter += 1

                        if not isinstance(gene, dict):
                            tqdm.write(
                                f"{Fore.YELLOW}WARNING: something went wrong!{Style.RESET_ALL}"
                            )
                            tqdm.write(f"Expected gene dict, got {type(gene)}: {gene}")
                            tqdm.write("")
                            raise TypeError("Invalid gene format")

                        transformed_gene = copy.deepcopy(gene)
                        transformed_gene["@type"] = "GeneExpression"
                        transformed_gene["ensemble_id"] = transformed_gene.pop(
                            "ensembl_id"
                        )
                        transformed_gene["mean_expression"] = transformed_gene.pop(
                            "mean_gene_expr_value"
                        )
                        keep_genes.append(transformed_gene)

                    transformed_summary["genes"] = keep_genes
                    keep_summary.append(transformed_summary)

                except Exception as e:
                    tqdm.write(
                        f"{Fore.YELLOW}Skipping summary due to error{Style.RESET_ALL}"
                    )
                    tqdm.write(str(e))
                    tqdm.write("")
                    tqdm.write(
                        f"{Fore.YELLOW}Skippimg summary {summary.get('cell_label', '<unknown>')}{Style.RESET_ALL}"
                    )
                    tqdm.write("")
                    continue

            if not keep_summary:
                continue

            out_obj = {
                k: copy.deepcopy(v)
                for k, v in obj.items()
                if k not in {"summary", "modality"}
            }
            out_obj["cell_source"] = cell_source
            out_obj["annotation_method"] = "Aggregation"
            out_obj["biomarker_type"] = "gene"
            out_obj["summary"] = keep_summary

            tqdm.write(
                f"Done making cell summary for {cell_source} with len = {len(keep_summary)}."
            )
            tqdm.write("")
            tqdm.write("======================")
            tqdm.write("")

            out_json_ld["@graph"].append(out_obj)

    # Write to file
    tqdm.write(f"Now saving to {FTU_CELL_SUMMARIES_OUTPUT}")
    with open(FTU_CELL_SUMMARIES_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out_json_ld, f, ensure_ascii=False, indent=4)


def main():
    # Driver code

    build_ftu_cell_summaries_jsonld()


if __name__ == "__main__":
    main()
