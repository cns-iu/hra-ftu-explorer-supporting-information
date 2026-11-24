#!/usr/bin/env python3
"""Compare cell counts per exact CL identifier in Anatomogram and HRApop.

This is the command-line Python version of the analyst-supplied frozen
notebook. It retains the original analysis definition: the 20 most abundant
Anatomogram author terms are compared with exact-ID counts from CellTypist,
Azimuth, and popV. Pan-Human Azimuth and FR-Match are not part of this
descriptive cell-count figure.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path
from unittest import result

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager


HRAPOP_METHODS = ("celltypist", "azimuth", "popv", "frmatch")
METHOD_LABELS = {
    "author": "Anatomogram author",
    "celltypist": "HRApop - CellTypist",
    "azimuth": "HRApop - Azimuth",
    "popv": "HRApop - popV",
    "frmatch": "HRApop - FR-Match",
    
}
COLORS = {
    "author": "#4D4D4D",
    "celltypist": "#0072B2",
    "azimuth": "#56B4E9",
    "popv": "#D55E00",
    "frmatch": "#009E73",
}
CL_PATTERN = re.compile(r"^CL:\d+$")
FIGURE_STEM = "task_01_cell_counts_per_ct_anatomogram_vs_hrapop"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instances", required=True, type=Path)
    parser.add_argument("--summaries", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--dpi", type=int, default=600)
    return parser.parse_args()


def is_cl_id(value: object) -> bool:
    return isinstance(value, str) and bool(CL_PATTERN.fullmatch(value.strip()))


def open_jsonl(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def load_anatomogram_author_counts(path: Path) -> pd.DataFrame:
    required = {"dataset", "cell", "tool", "cell_id", "cell_label"}
    data = pd.read_csv(path, dtype=str)
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Anatomogram input is missing columns: {sorted(missing)}")

    author = data.loc[data["tool"].eq("author")].copy()
    author = author.drop_duplicates(subset=["dataset", "cell"])
    return (
        author.groupby(["cell_id", "cell_label"], as_index=False, dropna=False)
        .size()
        .rename(columns={"size": "cell_count"})
    )


def load_hrapop_records(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with open_jsonl(path) as stream:
        for line_number, line in enumerate(stream, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}") from error
            if isinstance(item, dict):
                records.append(item)
    return records


def extract_hrapop_rows(records: list[dict[str, object]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for record_number, record in enumerate(records, start=1):
        method = str(record.get("annotation_method", "")).strip().lower()
        summary = record.get("summary", [])
        if isinstance(summary, dict):
            summary = [summary]
        if not isinstance(summary, list):
            continue

        for term in summary:
            if not isinstance(term, dict):
                continue
            cell_id = str(term.get("cell_id", "")).strip()
            if not cell_id:
                continue
            try:
                count = float(term.get("count"))
            except (TypeError, ValueError):
                continue
            try:
                percentage = float(term.get("percentage"))
            except (TypeError, ValueError):
                percentage = np.nan
            rows.append(
                {
                    "record_number": record_number,
                    "annotation_method": method,
                    "modality": str(record.get("modality", "")).strip(),
                    "cell_source": str(record.get("cell_source", "")).strip(),
                    "sex": record.get("sex", ""),
                    "cell_id": cell_id,
                    "cell_label": str(term.get("cell_label", "")).strip(),
                    "cell_count": count,
                    "percentage": percentage,
                }
            )

    if not rows:
        raise ValueError("No HRApop cell-type summary rows were found")
    return pd.DataFrame.from_records(rows)


def aggregate_hrapop_counts(raw: pd.DataFrame) -> pd.DataFrame:
    selected = raw.loc[raw["annotation_method"].isin(HRAPOP_METHODS)].copy()
    if selected.empty:
        raise ValueError(f"None of the expected methods were found: {HRAPOP_METHODS}")
    counts = (
        selected.groupby(["annotation_method", "cell_id"], as_index=False)
        .agg(
            cell_count=("cell_count", "sum"),
            hrapop_labels=(
                "cell_label",
                lambda values: " | ".join(
                    sorted({str(value).strip() for value in values if str(value).strip()})
                ),
            ),
        )
    )
    counts["is_cl_id"] = counts["cell_id"].map(is_cl_id)
    return counts


def build_comparison(
    author_counts: pd.DataFrame,
    hrapop_counts: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:
    top_author = (
        author_counts
        .sort_values("cell_count", ascending=False)
        .head(top_n)
        .copy()
    )

    top_ids = top_author["cell_id"].tolist()
    labels = top_author.set_index("cell_id")["cell_label"].to_dict()

    author = (
        top_author[["cell_id", "cell_count"]]
        .rename(columns={"cell_count": METHOD_LABELS["author"]})
        .set_index("cell_id")
    )

    hrapop = (
        hrapop_counts.loc[
            hrapop_counts["cell_id"].isin(top_ids)
        ]
        .pivot_table(
            index="cell_id",
            columns="annotation_method",
            values="cell_count",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(
            index=top_ids,
            columns=HRAPOP_METHODS,
            fill_value=0,
        )
        .rename(
            columns={
                method: METHOD_LABELS[method]
                for method in HRAPOP_METHODS
            }
        )
    )

    result = author.join(hrapop, how="left").fillna(0)
    result["cell_label"] = result.index.map(labels)
    result = result.reset_index()

    comparison_columns = [
        "cell_id",
        "cell_label",
        *[
            METHOD_LABELS[method]
            for method in ("author", *HRAPOP_METHODS)
        ],
    ]

    return result[comparison_columns]


def plot_comparison(comparison: pd.DataFrame, figure_dir: Path, dpi: int) -> None:
    sources = [METHOD_LABELS[method] for method in ("author", *HRAPOP_METHODS)]
    source_colors = {METHOD_LABELS[method]: COLORS[method] for method in ("author", *HRAPOP_METHODS)}
    plot_data = comparison.sort_values(METHOD_LABELS["author"], ascending=False).reset_index(drop=True)
    y = np.arange(len(plot_data))
    group_height = 0.84
    bar_height = group_height / len(sources)
    offsets = (np.arange(len(sources)) - (len(sources) - 1) / 2) * bar_height
    figure_height = 0.6 * len(plot_data) + 2.4

    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    plt.rcParams["font.family"] = "Arial" if "Arial" in available_fonts else "DejaVu Sans"
    plt.rcParams["pdf.fonttype"] = 42
    fig, axis = plt.subplots(figsize=(13, figure_height))
    axis.set_xscale("log")
    x_min = 1e2
    maximum = plot_data[sources].to_numpy(dtype=float).max()
    x_max = 10 ** np.ceil(np.log10(max(maximum, x_min)))
    axis.set_xlim(x_min, x_max)

    for offset, source in zip(offsets, sources):
        values = plot_data[source].to_numpy(dtype=float)
        positive = values > 0
        axis.barh(
            y[positive] + offset,
            values[positive],
            height=bar_height,
            left=x_min,
            color=source_colors[source],
            edgecolor="white",
            linewidth=0.4,
            label=source,
        )
        axis.scatter(
            np.full((~positive).sum(), x_min * 1.12),
            y[~positive] + offset,
            s=18,
            marker="o",
            facecolors="none",
            edgecolors=source_colors[source],
            linewidths=0.7,
            clip_on=False,
            zorder=3,
        )

    axis.set_yticks(y)
    axis.set_yticklabels(plot_data["cell_label"].tolist(), fontsize=14)
    axis.invert_yaxis()
    axis.set_ylim(len(plot_data) - 0.5, -0.5)
    axis.tick_params(axis="y", length=0, pad=6)
    axis.tick_params(axis="x", labelsize=14)
    axis.set_xlabel("Number of cells (log scale)", fontsize=14)
    for boundary in y[:-1] + 0.5:
        axis.axhline(boundary, color="#E5E5E5", linewidth=0.6, zorder=0)
    axis.grid(axis="x", which="major", color="#D9D9D9", linewidth=0.6)
    axis.set_axisbelow(True)
    for side in ("top", "right", "left"):
        axis.spines[side].set_visible(False)

    handles, labels = axis.get_legend_handles_labels()
    zero_handle = plt.Line2D(
        [],
        [],
        marker="o",
        linestyle="none",
        markersize=6,
        markerfacecolor="none",
        markeredgecolor="#4D4D4D",
        markeredgewidth=0.7,
    )
    axis.legend(
        handles + [zero_handle],
        labels + ["0 cells (no exact CL ID match)"],
        frameon=False,
        ncol=3,
        fontsize=12,
        loc="lower left",
        bbox_to_anchor=(0, 1.0),
        borderaxespad=0.4,
        handlelength=1.2,
        columnspacing=1.2,
    )
    axis.set_title("Cell counts per CT in Anatomogram and HRApop", fontsize=18, loc="left", pad=62)
    fig.tight_layout()

    figure_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_dir / f"{FIGURE_STEM}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(figure_dir / f"{FIGURE_STEM}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(figure_dir / f"{FIGURE_STEM}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    args = arguments()
    if not args.instances.exists():
        raise FileNotFoundError(f"Anatomogram input not found: {args.instances}")
    if not args.summaries.exists():
        raise FileNotFoundError(f"HRApop input not found: {args.summaries}")

    table_dir = args.output_dir / "tables" / "cell_counts"
    figure_dir = args.output_dir / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)

    author_counts = load_anatomogram_author_counts(args.instances)
    raw_hrapop = extract_hrapop_rows(load_hrapop_records(args.summaries))
    hrapop_counts = aggregate_hrapop_counts(raw_hrapop)
    comparison = build_comparison(author_counts, hrapop_counts, args.top_n)

    author_counts.to_csv(table_dir / "anatomogram_author_ct_counts.csv", index=False)
    raw_hrapop.to_csv(table_dir / "hrapop_ct_counts_raw.csv", index=False)
    hrapop_counts.to_csv(table_dir / "hrapop_ct_counts_by_tool.csv", index=False)
    comparison.to_csv(table_dir / "anatomogram_vs_hrapop_ct_counts.csv", index=False)
    plot_comparison(comparison, figure_dir, args.dpi)

    print(f"Wrote cell-count tables to {table_dir}")
    print(f"Wrote cell-count figure to {figure_dir}")


if __name__ == "__main__":
    main()
