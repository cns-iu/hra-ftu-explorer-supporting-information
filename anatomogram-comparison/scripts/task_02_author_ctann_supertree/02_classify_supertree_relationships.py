#!/usr/bin/env python3
"""Classify paired author and CTann annotations using the supplied supertree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict, deque
from pathlib import Path

import pandas as pd


CL_PATTERN = re.compile(r"^CL:\d+$")
RELATIONSHIPS = ("Exact", "CTann narrower", "CTann broader", "Different branch", "Unmapped")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paired-annotations", required=True, type=Path)
    parser.add_argument("--supertree", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def valid_cl(value: object) -> bool:
    return isinstance(value, str) and bool(CL_PATTERN.fullmatch(value.strip()))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def build_graph(tree: pd.DataFrame):
    levels = range(1, 13)
    adjacency: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    labels: dict[str, str] = {}
    anomalies: list[dict[str, object]] = []
    edges: set[tuple[str, str]] = set()

    for row_index, row in tree.iterrows():
        path: list[str] = []
        for level in levels:
            as_value = str(row.get(f"AS/{level}", "") or "").strip()
            id_value = str(row.get(f"AS/{level}/ID", "") or "").strip()
            label_value = str(row.get(f"AS/{level}/LABEL", "") or "").strip()

            if valid_cl(id_value):
                cell_id = id_value
                label = label_value or as_value
            elif id_value and valid_cl(label_value):
                cell_id = label_value
                label = id_value or as_value
                anomalies.append(
                    {
                        "csv_line": row_index + 2,
                        "level": level,
                        "issue": "swapped_id_and_label_recovered",
                        "raw_id": id_value,
                        "raw_label": label_value,
                        "resolved_id": cell_id,
                        "resolved_label": label,
                    }
                )
            else:
                if id_value:
                    anomalies.append(
                        {
                            "csv_line": row_index + 2,
                            "level": level,
                            "issue": "invalid_non_cl_identifier_skipped",
                            "raw_id": id_value,
                            "raw_label": label_value,
                            "resolved_id": "",
                            "resolved_label": "",
                        }
                    )
                elif as_value or label_value:
                    anomalies.append(
                        {
                            "csv_line": row_index + 2,
                            "level": level,
                            "issue": "label_without_cl_identifier_skipped",
                            "raw_id": "",
                            "raw_label": label_value or as_value,
                            "resolved_id": "",
                            "resolved_label": "",
                        }
                    )
                continue

            if cell_id in labels and label and labels[cell_id].casefold() != label.casefold():
                raise ValueError(
                    f"Conflicting labels for {cell_id}: {labels[cell_id]!r} and {label!r}"
                )
            labels.setdefault(cell_id, label)
            if path and path[-1] == cell_id:
                anomalies.append(
                    {
                        "csv_line": row_index + 2,
                        "level": level,
                        "issue": "adjacent_repeated_node_removed",
                        "raw_id": cell_id,
                        "raw_label": label,
                        "resolved_id": cell_id,
                        "resolved_label": label,
                    }
                )
                continue
            path.append(cell_id)

        for parent, child in zip(path, path[1:]):
            if parent == child:
                continue
            adjacency[parent].add(child)
            reverse[child].add(parent)
            edges.add((parent, child))
        for node in path:
            adjacency[node]
            reverse[node]

    nodes = set(adjacency) | set(reverse)
    indegree = {node: len(reverse[node]) for node in nodes}
    queue = deque(node for node, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for child in adjacency[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if visited != len(nodes):
        raise ValueError("The normalized supertree contains a directed cycle")

    undirected = {node: set(adjacency[node]) | set(reverse[node]) for node in nodes}
    component_count = 0
    unseen = set(nodes)
    while unseen:
        component_count += 1
        stack = [unseen.pop()]
        while stack:
            node = stack.pop()
            neighbours = undirected[node] & unseen
            unseen -= neighbours
            stack.extend(neighbours)
    roots = sorted(node for node in nodes if not reverse[node])
    if component_count != 1 or roots != ["CL:0000000"]:
        raise ValueError(f"Unexpected graph structure: components={component_count}, roots={roots}")

    return adjacency, reverse, labels, edges, anomalies, component_count, roots


def reachable(start: str, target: str, adjacency: dict[str, set[str]], cache: dict[str, set[str]]) -> bool:
    if start not in cache:
        found: set[str] = set()
        stack = list(adjacency.get(start, set()))
        while stack:
            node = stack.pop()
            if node in found:
                continue
            found.add(node)
            stack.extend(adjacency.get(node, set()) - found)
        cache[start] = found
    return target in cache[start]


def classify(author_id: str, ctann_id: str, nodes: set[str], adjacency, cache) -> str:
    if author_id == ctann_id:
        return "Exact"
    if author_id not in nodes or ctann_id not in nodes:
        return "Unmapped"
    if reachable(author_id, ctann_id, adjacency, cache):
        return "CTann narrower"
    if reachable(ctann_id, author_id, adjacency, cache):
        return "CTann broader"
    return "Different branch"


def summarize(group: pd.DataFrame) -> dict[str, object]:
    total = int(len(group))
    result: dict[str, object] = {"eligible_paired_cells": total}
    for relationship in RELATIONSHIPS:
        key = relationship.lower().replace(" ", "_")
        count = int(group["ontology_relationship"].eq(relationship).sum())
        result[f"{key}_cells"] = count
        result[f"{key}_fraction"] = count / total if total else None
    compatible = int(group["ontology_relationship"].isin(("Exact", "CTann narrower", "CTann broader")).sum())
    result["ontology_compatible_cells"] = compatible
    result["ontology_compatible_fraction"] = compatible / total if total else None
    return result


def main() -> None:
    args = arguments()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pairs = pd.read_csv(args.paired_annotations, dtype=str)
    for column in ("strict_eligible", "exact_cl_id", "author_valid_cl", "ctann_valid_cl"):
        if column in pairs:
            pairs[column] = pairs[column].astype(str).str.lower().eq("true")
    eligible = pairs.loc[pairs["strict_eligible"]].copy()

    tree = pd.read_csv(args.supertree, dtype=str, keep_default_na=False)
    adjacency, reverse, labels, edges, anomalies, components, roots = build_graph(tree)
    nodes = set(labels)
    cache: dict[str, set[str]] = {}
    eligible["author_in_supertree"] = eligible["author_id"].isin(nodes)
    eligible["ctann_in_supertree"] = eligible["ctann_id"].isin(nodes)
    eligible["ontology_relationship"] = [
        classify(a, c, nodes, adjacency, cache)
        for a, c in zip(eligible["author_id"], eligible["ctann_id"])
    ]
    eligible.to_csv(args.output_dir / "ontology_classified_pairs.csv.gz", index=False, compression="gzip")

    overall_rows = []
    for (method, label), group in eligible.groupby(["annotation_method", "method_label"]):
        overall_rows.append(
            {"annotation_method": method, "method_label": label, **summarize(group)}
        )
    pd.DataFrame(overall_rows).to_csv(args.output_dir / "ontology_overall_by_method.csv", index=False)

    organ_rows = []
    for (method, label, organ), group in eligible.groupby(
        ["annotation_method", "method_label", "organ_label"]
    ):
        organ_rows.append(
            {
                "annotation_method": method,
                "method_label": label,
                "organ_label": organ,
                **summarize(group),
            }
        )
    pd.DataFrame(organ_rows).to_csv(args.output_dir / "ontology_by_organ_method.csv", index=False)

    mapping_rows = []
    for role, id_column in (("author", "author_id"), ("ctann", "ctann_id")):
        grouping = ["annotation_method", "method_label"] if role == "ctann" else []
        groups = eligible.groupby(grouping) if grouping else [("all", eligible)]
        for key, group in groups:
            if role == "ctann":
                method, label = key
            else:
                method, label = "all", "Author"
            mapped = group[id_column].isin(nodes)
            mapping_rows.append(
                {
                    "annotation_role": role,
                    "annotation_method": method,
                    "method_label": label,
                    "annotation_rows": int(len(group)),
                    "mapped_rows": int(mapped.sum()),
                    "mapped_row_fraction": float(mapped.mean()) if len(group) else None,
                    "unique_cl_ids": int(group[id_column].nunique()),
                    "mapped_unique_cl_ids": int(group.loc[mapped, id_column].nunique()),
                }
            )
    pd.DataFrame(mapping_rows).to_csv(args.output_dir / "supertree_mapping_coverage.csv", index=False)

    pd.DataFrame(
        [{"parent_id": parent, "child_id": child} for parent, child in sorted(edges)]
    ).to_csv(args.output_dir / "normalized_supertree_edges.csv", index=False)
    pd.DataFrame(
        [{"cell_id": node, "cell_label": labels[node]} for node in sorted(nodes)]
    ).to_csv(args.output_dir / "normalized_supertree_nodes.csv", index=False)
    pd.DataFrame(anomalies).to_csv(args.output_dir / "supertree_normalization_log.csv", index=False)

    qc = {
        "input_sha256": {
            "paired_annotations": digest(args.paired_annotations),
            "supertree": digest(args.supertree),
        },
        "graph": {
            "valid_cl_nodes": len(nodes),
            "edges": len(edges),
            "weak_components": components,
            "roots": roots,
            "is_directed_acyclic_graph": True,
            "normalization_events": len(anomalies),
        },
        "eligible_paired_rows": int(len(eligible)),
        "classification_denominator": "paired cells with valid CL identifiers on both sides",
        "valid_ids_absent_from_tree_policy": "retained as Unmapped",
    }
    with (args.output_dir / "supertree_qc.json").open("w", encoding="utf-8") as stream:
        json.dump(qc, stream, indent=2)

    print(pd.DataFrame(overall_rows).to_string(index=False))


if __name__ == "__main__":
    main()
