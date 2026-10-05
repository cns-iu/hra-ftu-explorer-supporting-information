from shared import *
import itertools
from collections import Counter, defaultdict

import pandas as pd

# Keys in ftu_ct_conditions[ftu_label] holding CT lists (vs. organ metadata)
CONDITIONS = ("in_2d_ftu", "in_asctb", "exclusive_ct_in_ftu")

# A dataset can have one cell summary per annotation method (tool). To never count
# the same cells twice, each dataset is counted from exactly one tool: the first
# one in this order that the dataset has a cell summary for
ANNOTATION_METHOD_PREFERENCE = ("azimuth", "celltypist", "popv", "fr-match", "pan-human-azimuth")


def normalize_method(method: str) -> str:
    """Compare tool names ignoring case and separators (e.g. "FR-Match" == "fr_match")."""
    return "".join(char for char in method.lower() if char.isalnum())


def method_rank(method: str) -> int:
    """Position of a tool in ANNOTATION_METHOD_PREFERENCE; unknown tools rank last."""
    preference = [normalize_method(m) for m in ANNOTATION_METHOD_PREFERENCE]
    method = normalize_method(method)
    return preference.index(method) if method in preference else len(preference)


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
    # {ftu_label: (organ_curie, organ_label)}; each FTU has exactly one organ IRI, but the
    # source labels vary in case/wording (e.g. "Liver"/"liver", "skin"/"skin of body"), so
    # lowercase them and keep the most frequent one
    ftu_to_organ = {
        ftu_label: (
            iri_to_curie(group["organ_iri"].iloc[0]),
            group["organ_label"].str.lower().mode().iloc[0],
        )
        for ftu_label, group in ftu_query_result.groupby("ftu_label")
    }

    ftu_ct_conditions = {
        ftu_label: {
            "organ_id": ftu_to_organ[ftu_label][0],
            "organ_label": ftu_to_organ[ftu_label][1],
            "in_2d_ftu": ftu_to_cts_in_2d_ftu.get(ftu_label, []),
            "in_asctb": ftu_to_cts_in_asctb.get(ftu_label, []),
            "exclusive_ct_in_ftu": ftu_to_cts_exclusive.get(ftu_label, []),
        }
        for ftu_label in all_ftu_labels
    }

    for ftu_conditions in ftu_ct_conditions.values():
        for condition in CONDITIONS:
            cell_types = ftu_conditions[condition]
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


def load_dataset_to_paper():
    """Map each HRApop universe dataset_id (== cell_source) to its paper DOI
    (None if the dataset has no DOI). The sankey report has one row per dataset
    and collision, but at most one DOI per dataset."""
    sankey = pd.read_csv(UNIVERSE_SANKEY_URL, usecols=["dataset_id", "doi"])
    sankey = sankey.drop_duplicates("dataset_id")
    return {
        dataset_id: doi if pd.notna(doi) else None
        for dataset_id, doi in zip(sankey["dataset_id"], sankey["doi"])
    }


def parse_universe_cell_summaries(
    ftu_ct_conditions: dict,
    ftu_to_organs: dict,
    dataset_to_organ: dict,
    dataset_to_paper: dict,
    sample_size: int | None = None,
):
    """For each FTU/condition, count the distinct datasets (cell_source) in the
    HRApop universe that come from the FTU's organ and contain a CT satisfying
    that condition, plus the number of cells of those CTs in those datasets, and
    add them under ftu_ct_conditions[ftu_label]["datasets_with_ct_by_<condition>"]
    and ["cells_with_ct_by_<condition>"].

    A dataset can have one cell summary per annotation method (tool), so to
    avoid counting the same cells more than once, each dataset is counted from a
    single tool: the most preferred one (ANNOTATION_METHOD_PREFERENCE) it has a
    cell summary for, whether or not that tool found CTs for a given FTU. This
    applies to both the dataset and the cell counts, so a dataset only counts for
    an FTU/condition if its chosen tool found a matching CT.

    The papers of those counted datasets are added under
    ftu_ct_conditions[ftu_label]["papers_for_this_ftu_by_dataset"][condition]
    as {dataset_id: doi} (doi is None for datasets without one).

    sample_size caps how many universe records are scanned (the full file is huge
    and slow to process); pass None (default) to scan the whole file.
    """
    # Reverse index: ct_curie -> {(ftu_label, condition), ...}, built once up front
    # so the big-file scan below is O(1) per cell type instead of re-searching
    # the whole ftu_ct_conditions dict for every row. A set, so a CT listed twice
    # (e.g. under two labels) isn't counted twice.
    curie_to_hits = defaultdict(set)
    for ftu_label, conditions in ftu_ct_conditions.items():
        for condition in CONDITIONS:
            for cell_type in conditions[condition]:
                curie_to_hits[cell_type["ct_curie"]].add((ftu_label, condition))

    # {ftu_label: {condition: {cell_source: {annotation_method: cell_count}}}}
    cells_by_condition = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )

    universe = iterate_through_json_lines(UNIVERSE_10K_FILENAME)
    datasets_without_organ = set()
    # {cell_source: {annotation_method: number of cell summaries}}
    methods_per_dataset = defaultdict(lambda: defaultdict(int))
    for obj in itertools.islice(universe, sample_size):
        cell_source = obj["cell_source"]
        organ = dataset_to_organ.get(cell_source)
        if organ is None:
            datasets_without_organ.add(cell_source)
            continue
        method = obj["annotation_method"]
        methods_per_dataset[cell_source][method] += 1
        for cell_type in obj["summary"]:
            for ftu_label, condition in curie_to_hits.get(cell_type["cell_id"], ()):
                if organ in ftu_to_organs.get(ftu_label, ()):
                    cells_by_condition[ftu_label][condition][cell_source][method] += cell_type["count"]

    if datasets_without_organ:
        print(f"Skipped {len(datasets_without_organ)} datasets with no organ in the universe metadata.")

    methods_seen = {method for methods in methods_per_dataset.values() for method in methods}
    print(f"Annotation methods seen: {sorted(methods_seen)}")
    unknown_methods = {m for m in methods_seen if method_rank(m) == len(ANNOTATION_METHOD_PREFERENCE)}
    if unknown_methods:
        print(f"WARNING: annotation methods not in ANNOTATION_METHOD_PREFERENCE: {sorted(unknown_methods)}")
    repeated = sum(count > 1 for methods in methods_per_dataset.values() for count in methods.values())
    if repeated:
        print(f"WARNING: {repeated} (dataset, annotation method) pairs have more than one cell summary; their cells are summed.")

    chosen_method = {
        cell_source: min(methods, key=method_rank)
        for cell_source, methods in methods_per_dataset.items()
    }
    print(f"Datasets per chosen annotation method: {dict(Counter(chosen_method.values()))}")

    datasets_without_paper = set()
    for ftu_label, conditions in ftu_ct_conditions.items():
        conditions["papers_for_this_ftu_by_dataset"] = {}
        for condition in CONDITIONS:
            # {cell_source: cell count from its chosen tool}
            cells_per_dataset = {
                cell_source: cells_per_method[chosen_method[cell_source]]
                for cell_source, cells_per_method in cells_by_condition[ftu_label][condition].items()
                if chosen_method[cell_source] in cells_per_method
            }
            conditions[f"datasets_with_ct_by_{condition}"] = len(cells_per_dataset)
            conditions[f"cells_with_ct_by_{condition}"] = sum(cells_per_dataset.values())
            conditions["papers_for_this_ftu_by_dataset"][condition] = {
                cell_source: dataset_to_paper.get(cell_source)
                for cell_source in sorted(cells_per_dataset)
            }
            datasets_without_paper.update(
                cell_source for cell_source in cells_per_dataset
                if dataset_to_paper.get(cell_source) is None
            )

    if datasets_without_paper:
        print(f"{len(datasets_without_paper)} counted datasets have no paper DOI in the sankey report.")

    return ftu_ct_conditions


def build_ftu_ct_conditions_df(ftu_ct_conditions):
    """Flatten ftu_ct_conditions into one row per FTU: organ, then per condition
    the CT count, the "; "-joined CT labels, and the dataset and cell counts."""
    records = []
    for ftu_label, conditions in ftu_ct_conditions.items():
        record = {
            "ftu_label": ftu_label,
            "organ_id": conditions["organ_id"],
            "organ_label": conditions["organ_label"],
        }
        for condition in CONDITIONS:
            cell_types = conditions[condition]
            record[f"{condition}_ct_count"] = len(cell_types)
            record[f"{condition}_ct_labels"] = "; ".join(ct["ct_label"] for ct in cell_types)
            record[f"datasets_with_ct_by_{condition}"] = conditions[f"datasets_with_ct_by_{condition}"]
            record[f"cells_with_ct_by_{condition}"] = conditions[f"cells_with_ct_by_{condition}"]
            papers = {
                doi for doi in conditions["papers_for_this_ftu_by_dataset"][condition].values()
                if doi is not None
            }
            record[f"papers_with_ct_by_{condition}"] = len(papers)
            record[f"papers_with_ct_by_{condition}_dois"] = "; ".join(sorted(papers))
        records.append(record)
    return pd.DataFrame(records)


def main():
    ct_counts_in_ftu_illustrations, ftu_ct_conditions, ftu_to_organs = load_ftu_query_and_count()
    dataset_to_organ = load_dataset_to_organ()
    dataset_to_paper = load_dataset_to_paper()
    ftu_ct_conditions = parse_universe_cell_summaries(
        ftu_ct_conditions, ftu_to_organs, dataset_to_organ, dataset_to_paper
    )

    # Save results
    save_df(ct_counts_in_ftu_illustrations, "cell_types_and_datasets_per_ftu.csv")
    save_json(ftu_ct_conditions, "ftu_ct_conditions.json")
    save_df(build_ftu_ct_conditions_df(ftu_ct_conditions), "ftu_ct_conditions.csv")

if __name__ == "__main__":
    main()
