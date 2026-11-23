#!/usr/bin/env python3
"""Prepare strict author-versus-CTann cell pairs and method availability tables."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd


METHODS = ("celltypist", "azimuth", "popv", "frmatch")
METHOD_LABELS = {
    "celltypist": "CellTypist",
    "azimuth": "Azimuth",
    "popv": "popV",
    "frmatch": "FR-Match",
}
ORGAN_LABELS = {
    "UBERON:0002113": "Kidney",
    "UBERON:0002107": "Liver",
    "UBERON:0002048": "Lung",
    "UBERON:0001264": "Pancreas",
}
CL_PATTERN = re.compile(r"^CL:\d+$")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances", required=True, type=Path)
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


def safe_rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def summary_row(method: str, organ: str, applicable: pd.DataFrame, pairs: pd.DataFrame) -> dict[str, object]:
    applicable_n = int(len(applicable))
    paired_n = int(len(pairs))
    eligible_n = int(pairs["strict_eligible"].sum()) if paired_n else 0
    exact_n = int(pairs["exact_cl_id"].sum()) if paired_n else 0
    invalid_author_n = int((~pairs["author_valid_cl"]).sum()) if paired_n else 0

    if not applicable_n:
        status = "not_run"
    elif not paired_n and method == "frmatch":
        status = "unavailable_identifier_crosswalk"
    elif not paired_n:
        status = "no_matched_cell_identifiers"
    else:
        status = "available"

    return {
        "annotation_method": method,
        "method_label": METHOD_LABELS[method],
        "organ_label": organ,
        "status": status,
        "applicable_author_cells": applicable_n,
        "paired_cells": paired_n,
        "pairing_coverage": safe_rate(paired_n, applicable_n) if status == "available" else None,
        "strict_eligible_cells": eligible_n,
        "exact_cl_id_matches": exact_n,
        "exact_agreement": safe_rate(exact_n, eligible_n),
        "provisional_author_cells_in_pairs": invalid_author_n,
    }


def main() -> None:
    args = arguments()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    instances = pd.read_csv(args.instances, dtype=str)
    required = {
        "dataset",
        "organ",
        "tool",
        "cell",
        "cell_id",
        "cell_label",
        "match_type",
        "confidence_score",
    }
    missing = required - set(instances.columns)
    if missing:
        raise ValueError(f"Instances file is missing columns: {sorted(missing)}")
    instances["organ_label"] = instances["organ"].map(ORGAN_LABELS)
    if instances["organ_label"].isna().any():
        bad = sorted(instances.loc[instances["organ_label"].isna(), "organ"].unique())
        raise ValueError(f"Unexpected organs: {bad}")

    selected = instances.loc[instances["tool"].isin(("author",) + METHODS)].copy()
    duplicate_counts = selected.groupby(["dataset", "cell", "tool"]).size()
    duplicate_counts = duplicate_counts.loc[duplicate_counts.gt(1)]
    if not duplicate_counts.empty:
        raise ValueError(f"Found {len(duplicate_counts)} duplicate dataset-cell-tool groups")

    author = selected.loc[selected["tool"].eq("author")].copy()
    author_conflicts = author.groupby(["dataset", "cell"])["cell_id"].nunique(dropna=False)
    author_conflicts = author_conflicts.loc[author_conflicts.gt(1)]
    if not author_conflicts.empty:
        raise ValueError(f"Found {len(author_conflicts)} conflicting author annotations")

    author = author.rename(columns={"cell_id": "author_id", "cell_label": "author_label"})
    author["author_valid_cl"] = author["author_id"].map(valid_cl)
    provisional = author.loc[~author["author_valid_cl"]].copy()
    (
        provisional.groupby(["author_id", "author_label", "organ_label"], dropna=False)
        .size()
        .rename("cell_count")
        .reset_index()
        .sort_values("cell_count", ascending=False)
        .to_csv(args.output_dir / "provisional_author_identifiers.csv", index=False)
    )

    pair_tables: list[pd.DataFrame] = []
    dataset_availability: list[dict[str, object]] = []
    organ_summary: list[dict[str, object]] = []
    overall_summary: list[dict[str, object]] = []

    for method in METHODS:
        tool = selected.loc[selected["tool"].eq(method)].copy()
        tool = tool.rename(
            columns={
                "cell_id": "ctann_id",
                "cell_label": "ctann_label",
                "match_type": "ctann_match_type",
                "confidence_score": "ctann_confidence_score",
            }
        )
        applicable_datasets = set(tool["dataset"])
        applicable_author = author.loc[author["dataset"].isin(applicable_datasets)].copy()
        pairs = applicable_author.merge(
            tool[
                [
                    "dataset",
                    "cell",
                    "ctann_id",
                    "ctann_label",
                    "ctann_match_type",
                    "ctann_confidence_score",
                ]
            ],
            on=["dataset", "cell"],
            how="inner",
            validate="one_to_one",
        )
        pairs["annotation_method"] = method
        pairs["method_label"] = METHOD_LABELS[method]
        pairs["ctann_valid_cl"] = pairs["ctann_id"].map(valid_cl)
        pairs["strict_eligible"] = pairs["author_valid_cl"] & pairs["ctann_valid_cl"]
        pairs["exact_cl_id"] = pairs["strict_eligible"] & pairs["author_id"].eq(pairs["ctann_id"])
        if not pairs.empty:
            pair_tables.append(pairs)

        for dataset in sorted(applicable_datasets):
            author_ds = author.loc[author["dataset"].eq(dataset)]
            tool_ds = tool.loc[tool["dataset"].eq(dataset)]
            shared = author_ds.merge(tool_ds[["dataset", "cell"]], on=["dataset", "cell"], how="inner")
            dataset_availability.append(
                {
                    "annotation_method": method,
                    "method_label": METHOD_LABELS[method],
                    "dataset": dataset,
                    "organ_label": tool_ds["organ_label"].iloc[0],
                    "author_cells": int(len(author_ds)),
                    "tool_annotation_rows": int(len(tool_ds)),
                    "shared_cell_identifiers": int(len(shared)),
                    "identifier_type_note": (
                        "numeric identifiers; barcode crosswalk unavailable"
                        if method == "frmatch"
                        else "cell barcodes"
                    ),
                }
            )

        for organ in ORGAN_LABELS.values():
            organ_applicable = applicable_author.loc[applicable_author["organ_label"].eq(organ)]
            organ_pairs = pairs.loc[pairs["organ_label"].eq(organ)]
            organ_summary.append(summary_row(method, organ, organ_applicable, organ_pairs))
        overall_summary.append(summary_row(method, "All applicable datasets", applicable_author, pairs))

    all_pairs = pd.concat(pair_tables, ignore_index=True) if pair_tables else pd.DataFrame()
    all_pairs.to_csv(args.output_dir / "paired_annotations.csv.gz", index=False, compression="gzip")
    pd.DataFrame(dataset_availability).to_csv(
        args.output_dir / "method_dataset_availability.csv", index=False
    )
    pd.DataFrame(organ_summary).to_csv(args.output_dir / "strict_by_organ_method.csv", index=False)
    pd.DataFrame(overall_summary).to_csv(args.output_dir / "strict_overall_by_method.csv", index=False)

    qc = {
        "input_sha256": digest(args.instances),
        "selected_methods": list(METHODS),
        "excluded_method": "pan-human-azimuth",
        "exact_denominator": "paired cells with valid CL identifiers on both sides",
        "author_cells": int(len(author)),
        "valid_author_cells": int(author["author_valid_cl"].sum()),
        "provisional_author_cells": int((~author["author_valid_cl"]).sum()),
        "paired_rows": int(len(all_pairs)),
        "duplicate_dataset_cell_tool_groups": int(len(duplicate_counts)),
        "conflicting_author_annotations": int(len(author_conflicts)),
    }
    with (args.output_dir / "pairing_qc.json").open("w", encoding="utf-8") as stream:
        json.dump(qc, stream, indent=2)

    print(pd.DataFrame(overall_summary).to_string(index=False))


if __name__ == "__main__":
    main()
