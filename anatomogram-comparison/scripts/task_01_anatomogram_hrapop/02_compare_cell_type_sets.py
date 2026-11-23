#!/usr/bin/env python3
"""Compare Anatomogram and HRApop CL-term sets by organ/dataset.

HRApop is the union of CellTypist, Azimuth, popV, and FR-Match. Pan-Human
Azimuth is excluded by design. Only syntactically valid CL identifiers enter
the set comparison; provisional author identifiers are reported separately.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd


METHODS = ("celltypist", "azimuth", "popv", "frmatch")
METHOD_LABELS = {
    "author": "Anatomogram author",
    "celltypist": "HRApop - CellTypist",
    "azimuth": "HRApop - Azimuth",
    "popv": "HRApop - popV",
    "frmatch": "HRApop - FR-Match",
}
ORGAN_LABELS = {
    "UBERON:0002113": "Kidney",
    "UBERON:0002107": "Liver",
    "UBERON:0002048": "Lung",
    "UBERON:0001264": "Pancreas",
}
ORGAN_ORDER = ("Kidney", "Liver", "Lung", "Pancreas")
CATEGORY_ORDER = ("Shared", "Anatomogram only", "HRApop only")
CL_PATTERN = re.compile(r"^CL:\d+$")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances", required=True, type=Path)
    parser.add_argument("--summaries", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--terms-per-category", type=int, default=4)
    return parser.parse_args()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def get_accession(value: object) -> str:
    match = re.search(r"/experiments/([^#]+)", str(value))
    if not match:
        raise ValueError(f"Cannot extract dataset accession from {value!r}")
    return match.group(1)


def valid_cl(value: object) -> bool:
    return isinstance(value, str) and bool(CL_PATTERN.fullmatch(value.strip()))


def preferred_label(values: pd.Series) -> str:
    labels = [str(v).strip() for v in values if isinstance(v, str) and str(v).strip()]
    return Counter(labels).most_common(1)[0][0] if labels else ""


def open_jsonl(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def main() -> None:
    args = arguments()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    columns = ["dataset", "organ", "tool", "cell", "cell_id", "cell_label"]
    instances = pd.read_csv(args.instances, usecols=columns, dtype=str)
    instances["accession"] = instances["dataset"].map(get_accession)
    instances["organ_label"] = instances["organ"].map(ORGAN_LABELS)
    if instances["organ_label"].isna().any():
        bad = sorted(instances.loc[instances["organ_label"].isna(), "organ"].unique())
        raise ValueError(f"Unexpected organs: {bad}")

    duplicate_groups = instances.groupby(["dataset", "cell", "tool"]).size()
    duplicate_groups = duplicate_groups.loc[duplicate_groups.gt(1)]
    if not duplicate_groups.empty:
        raise ValueError(f"Found {len(duplicate_groups)} duplicate dataset-cell-tool groups")

    author = instances.loc[instances["tool"].eq("author")].copy()
    author_conflicts = author.groupby(["dataset", "cell"])["cell_id"].nunique(dropna=False)
    author_conflicts = author_conflicts.loc[author_conflicts.gt(1)]
    if not author_conflicts.empty:
        raise ValueError(f"Found {len(author_conflicts)} conflicting author annotations")

    valid_author = author.loc[author["cell_id"].map(valid_cl)].copy()
    invalid_author = author.loc[~author["cell_id"].map(valid_cl)].copy()
    author_counts = (
        valid_author.groupby(
            ["accession", "organ", "organ_label", "cell_id"], as_index=False
        )
        .agg(cell_label=("cell_label", preferred_label), cell_count=("cell", "nunique"))
    )
    author_counts["annotation_method"] = "author"

    records: list[dict[str, object]] = []
    summary_totals: Counter[str] = Counter()
    with open_jsonl(args.summaries) as stream:
        for line_number, line in enumerate(stream, start=1):
            item = json.loads(line)
            method = str(item.get("annotation_method", "")).strip().lower()
            if method not in METHODS:
                continue
            acc = get_accession(item.get("cell_source", ""))
            organ_ids = instances.loc[instances["accession"].eq(acc), "organ"].unique()
            if len(organ_ids) != 1:
                raise ValueError(f"Dataset {acc} maps to {len(organ_ids)} organs")
            organ = organ_ids[0]
            for term in item.get("summary", []):
                cell_id = str(term.get("cell_id", "")).strip()
                if not valid_cl(cell_id):
                    continue
                count = int(term.get("count", 0))
                summary_totals[method] += count
                records.append(
                    {
                        "accession": acc,
                        "organ": organ,
                        "organ_label": ORGAN_LABELS[organ],
                        "cell_id": cell_id,
                        "cell_label": str(term.get("cell_label", "")).strip(),
                        "cell_count": count,
                        "annotation_method": method,
                        "summary_line": line_number,
                    }
                )

    hrapop = pd.DataFrame.from_records(records)
    if hrapop.empty:
        raise ValueError("No HRApop summary records found for the selected methods")
    hrapop_counts = (
        hrapop.groupby(
            ["accession", "organ", "organ_label", "cell_id", "annotation_method"],
            as_index=False,
        )
        .agg(cell_label=("cell_label", preferred_label), cell_count=("cell_count", "sum"))
    )
    counts = pd.concat([author_counts, hrapop_counts], ignore_index=True)
    counts["source_label"] = counts["annotation_method"].map(METHOD_LABELS)

    category_records: list[dict[str, object]] = []
    for (acc, organ), group in counts.groupby(["accession", "organ_label"], sort=False):
        author_ids = set(group.loc[group["annotation_method"].eq("author"), "cell_id"])
        hrapop_ids = set(group.loc[~group["annotation_method"].eq("author"), "cell_id"])
        for cell_id in sorted(author_ids | hrapop_ids):
            if cell_id in author_ids and cell_id in hrapop_ids:
                category = "Shared"
            elif cell_id in author_ids:
                category = "Anatomogram only"
            else:
                category = "HRApop only"
            rows = group.loc[group["cell_id"].eq(cell_id)]
            category_records.append(
                {
                    "accession": acc,
                    "organ_label": organ,
                    "cell_id": cell_id,
                    "cell_label": preferred_label(rows["cell_label"]),
                    "category": category,
                    "total_cell_count": int(rows["cell_count"].sum()),
                    "max_source_cell_count": int(rows["cell_count"].max()),
                    "number_of_sources": int(rows["annotation_method"].nunique()),
                }
            )

    categories = pd.DataFrame.from_records(category_records)
    categories["organ_label"] = pd.Categorical(categories["organ_label"], ORGAN_ORDER, ordered=True)
    categories["category"] = pd.Categorical(categories["category"], CATEGORY_ORDER, ordered=True)
    categories = categories.sort_values(
        ["organ_label", "category", "max_source_cell_count", "cell_id"],
        ascending=[True, True, False, True],
        kind="stable",
    ).reset_index(drop=True)

    unique_counts = (
        categories.groupby(["accession", "organ_label", "category"], observed=True)
        .size()
        .rename("unique_ct_count")
        .reset_index()
    )
    selected = (
        categories.groupby(["accession", "organ_label", "category"], observed=True, group_keys=False)
        .head(args.terms_per_category)
        .copy()
    )
    selected["category_rank"] = selected.groupby(
        ["accession", "organ_label", "category"], observed=True
    ).cumcount() + 1
    selected_counts = counts.merge(
        selected[["accession", "organ_label", "cell_id", "category", "category_rank"]],
        on=["accession", "organ_label", "cell_id"],
        how="inner",
        validate="many_to_one",
    )

    counts.to_csv(args.output_dir / "source_specific_ct_counts.csv", index=False)
    categories.to_csv(args.output_dir / "all_ct_categories.csv", index=False)
    unique_counts.to_csv(args.output_dir / "unique_ct_counts.csv", index=False)
    selected.to_csv(args.output_dir / "selected_ct_terms.csv", index=False)
    selected_counts.to_csv(args.output_dir / "selected_ct_source_counts.csv", index=False)
    (
        invalid_author.groupby(["cell_id", "cell_label"], dropna=False)
        .size()
        .rename("cell_count")
        .reset_index()
        .sort_values("cell_count", ascending=False)
        .to_csv(args.output_dir / "provisional_author_identifiers.csv", index=False)
    )

    instance_totals = instances.groupby("tool").size().to_dict()
    qc = {
        "hrapop_methods": list(METHODS),
        "excluded_methods": ["pan-human-azimuth"],
        "input_sha256": {
            "instances": digest(args.instances),
            "summaries": digest(args.summaries),
        },
        "rows": {
            "instances": int(len(instances)),
            "author": int(len(author)),
            "valid_author": int(len(valid_author)),
            "provisional_author": int(len(invalid_author)),
        },
        "summary_count_reconciliation": {
            method: {
                "summary_count": int(summary_totals[method]),
                "instance_rows": int(instance_totals.get(method, 0)),
                "matches": int(summary_totals[method]) == int(instance_totals.get(method, 0)),
            }
            for method in METHODS
        },
    }
    with (args.output_dir / "task_01_qc.json").open("w", encoding="utf-8") as stream:
        json.dump(qc, stream, indent=2)

    print(unique_counts.to_string(index=False))


if __name__ == "__main__":
    main()
