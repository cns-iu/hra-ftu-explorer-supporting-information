from shared import *
import itertools
from collections import defaultdict

import pandas as pd


def build_ct_counts_df(ftu_ct_conditions):
    """Derive per-FTU CT counts from the ftu_ct_conditions dict."""
    records = [
        {
            "ftu_label": ftu_label,
            "ct_in_illustration_count": len(conditions["in_2d_ftu"]),
            "ct_iri_true_count": len(conditions["exclusive_ct_in_ftu"]),
        }
        for ftu_label, conditions in ftu_ct_conditions.items()
    ]
    return pd.DataFrame(records)


def load_ftu_query_and_count():
    # Load CTs per FTU illustration
    ftu_query_result = pd.read_csv(FTU_QUERY)
    pprint(ftu_query_result)

    # Look-ups: for every FTU, the {ct_label, ct_iri} pairs satisfying each condition individually
    def ftu_to_cts_where(column):
        filtered = (
            ftu_query_result[ftu_query_result[column] == True][["ftu_label", "ct_label", "ct_iri"]]
            .drop_duplicates()
        )
        return {
            ftu_label: group[["ct_label", "ct_iri"]].to_dict(orient="records")
            for ftu_label, group in filtered.groupby("ftu_label")
        }

    ftu_to_cts_in_2d_ftu = ftu_to_cts_where("in_2d_ftu")
    ftu_to_cts_in_asctb = ftu_to_cts_where("in_asctb")
    ftu_to_cts_exclusive = ftu_to_cts_where("exclusive_ct_in_ftu")

    # Combine into one dict: {ftu_label: {condition: [ct_iri, ...]}}
    all_ftu_labels = sorted(
        set(ftu_to_cts_in_2d_ftu) | set(ftu_to_cts_in_asctb) | set(ftu_to_cts_exclusive)
    )
    ftu_ct_conditions = {
        ftu_label: {
            "in_2d_ftu": ftu_to_cts_in_2d_ftu.get(ftu_label, []),
            "in_asctb": ftu_to_cts_in_asctb.get(ftu_label, []),
            "exclusive_ct_in_ftu": ftu_to_cts_exclusive.get(ftu_label, []),
        }
        for ftu_label in all_ftu_labels
    }

    for ftu_conditions in ftu_ct_conditions.values():
        for cell_types in ftu_conditions.values():
            for cell_type in cell_types:
                cell_type["ct_curie"] = iri_to_curie(cell_type["ct_iri"])

    pprint(ftu_ct_conditions)

    for ftu in ftu_ct_conditions:
        print(f"{ftu}: {len(ftu_ct_conditions[ftu]["in_2d_ftu"])} CTs in illustration.")
        print(
            f"{ftu}: {len(ftu_ct_conditions[ftu]["exclusive_ct_in_ftu"])} exclusive CTs."
        )
        print()

    ct_counts_in_ftu_illustrations = build_ct_counts_df(ftu_ct_conditions)
    pprint(ct_counts_in_ftu_illustrations)

    # {ftu_label: {organ_curie, ...}} so dataset counts can be restricted to the FTU's own organ
    ftu_to_organs = {
        ftu_label: {iri_to_curie(organ_iri) for organ_iri in group["organ_iri"].unique()}
        for ftu_label, group in ftu_query_result.groupby("ftu_label")
    }

    return ct_counts_in_ftu_illustrations, ftu_ct_conditions, ftu_to_organs


def load_dataset_to_organ():
    """Map each HRApop universe dataset_id (== cell_source) to its organ CURIE."""
    metadata = pd.read_csv(UNIVERSE_METADATA_URL, usecols=["dataset_id", "organ"])
    return dict(zip(metadata["dataset_id"], metadata["organ"]))


def parse_universe_cell_summaries(
    ftu_ct_conditions: dict,
    ftu_to_organs: dict,
    dataset_to_organ: dict,
    sample_size: int | None = None,
):
    """For each FTU/condition, count the distinct datasets (cell_source) in the
    HRApop universe that come from the FTU's organ and contain a CT satisfying
    that condition, and add it under
    ftu_ct_conditions[ftu_label]["datasets_with_ct_by_<condition>"].

    sample_size caps how many universe records are scanned (the full file is huge
    and slow to process); pass None (default) to scan the whole file.
    """
    # Reverse index: ct_curie -> [(ftu_label, condition), ...], built once up front
    # so the big-file scan below is O(1) per cell type instead of re-searching
    # the whole ftu_ct_conditions dict for every row.
    curie_to_hits = defaultdict(list)
    for ftu_label, conditions in ftu_ct_conditions.items():
        for condition, cell_types in conditions.items():
            for cell_type in cell_types:
                curie_to_hits[cell_type["ct_curie"]].append((ftu_label, condition))

    datasets_by_condition = defaultdict(lambda: defaultdict(set))

    universe = iterate_through_json_lines(UNIVERSE_10K_FILENAME)
    datasets_without_organ = set()
    for obj in itertools.islice(universe, sample_size):
        cell_source = obj["cell_source"]
        organ = dataset_to_organ.get(cell_source)
        if organ is None:
            datasets_without_organ.add(cell_source)
            continue
        for cell_type in obj["summary"]:
            for ftu_label, condition in curie_to_hits.get(cell_type["cell_id"], ()):
                if organ in ftu_to_organs.get(ftu_label, ()):
                    datasets_by_condition[ftu_label][condition].add(cell_source)

    if datasets_without_organ:
        print(f"Skipped {len(datasets_without_organ)} datasets with no organ in the universe metadata.")

    for ftu_label, conditions in ftu_ct_conditions.items():
        for condition in list(conditions.keys()):
            conditions[f"datasets_with_ct_by_{condition}"] = len(
                datasets_by_condition[ftu_label][condition]
            )

    return ftu_ct_conditions


def main():
    ct_counts_in_ftu_illustrations, ftu_ct_conditions, ftu_to_organs = load_ftu_query_and_count()
    dataset_to_organ = load_dataset_to_organ()
    ftu_ct_conditions = parse_universe_cell_summaries(
        ftu_ct_conditions, ftu_to_organs, dataset_to_organ
    )

    # Save results
    save_df(ct_counts_in_ftu_illustrations, "cell_types_and_datasets_per_ftu.csv")
    save_json(ftu_ct_conditions, "ftu_ct_conditions.json")

if __name__ == "__main__":
    main()
