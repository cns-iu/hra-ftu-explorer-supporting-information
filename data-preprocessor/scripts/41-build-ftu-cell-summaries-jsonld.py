from shared import *


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
        if obj_counter > 1022:
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

            tqdm.write("")
            tqdm.write(f"Now working on cell_source #{obj_counter}: {cell_source}")

            obj["cell_source"] = cell_source
            tqdm.write("")
            tqdm.write(f"Now making summary for {cell_source}")
            tqdm.write("")

            obj["annotation_method"] = "Aggregation"
            obj["biomarker_type"] = "gene"
            obj.pop("modality")

            keep_summary = []

            for summary in obj["summary"]:
                try:
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

                        gene_counter += 1

                        if not isinstance(gene, dict):
                            tqdm.write(
                                f"{Fore.YELLOW}WARNING: something went wrong!{Style.RESET_ALL}"
                            )
                            tqdm.write(f"Expected gene dict, got {type(gene)}: {gene}")
                            tqdm.write("")
                            raise TypeError(
                                "Invalid gene format"
                            )  # 🔑 triggers skip of summary

                        gene["@type"] = "GeneExpression"
                        gene["ensemble_id"] = gene.pop("ensembl_id")
                        gene["mean_expression"] = gene.pop("mean_gene_expr_value")

                        keep_genes.append(gene)

                    summary["genes"] = keep_genes
                    keep_summary.append(summary)

                except Exception as e:
                    tqdm.write(
                        f"{Fore.YELLOW}Skipping summary due to error{Style.RESET_ALL}"
                    )
                    tqdm.write(str(e))
                    tqdm.write("")
                    tqdm.write(
                        f"{Fore.YELLOW}Skippimg summary {summary['cell_label']}{Style.RESET_ALL}"
                    )
                    tqdm.write("")
                    continue  # 🔑 move to next summary

            obj["summary"] = keep_summary

            tqdm.write(
                f"Done making cell summary for {cell_source} with len = {len(summary)}."
            )
            tqdm.write("")
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

    build_ftu_cell_summaries_jsonld()


if __name__ == "__main__":
    main()
