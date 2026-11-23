#!/usr/bin/env python3
"""Generate the Task 1 Anatomogram-versus-HRApop manuscript figure."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch


METHOD_ORDER = ("author", "celltypist", "azimuth", "popv", "frmatch")
METHOD_LABELS = {
    "author": "Anatomogram author",
    "celltypist": "HRApop - CellTypist",
    "azimuth": "HRApop - Azimuth",
    "popv": "HRApop - popV",
    "frmatch": "HRApop - FR-Match",
}
METHOD_COLORS = {
    "author": "#555555",
    "celltypist": "#0072B2",
    "azimuth": "#56B4E9",
    "popv": "#D55E00",
    "frmatch": "#009E73",
}
ORGAN_ORDER = ("Kidney", "Liver", "Lung", "Pancreas")
CATEGORY_ORDER = ("Shared", "Anatomogram only", "HRApop only")
CATEGORY_BACKGROUNDS = {
    "Shared": "#E7F2F8",
    "Anatomogram only": "#F1F1F1",
    "HRApop only": "#FBEDE8",
}
CATEGORY_COLORS = {
    "Shared": "#0072B2",
    "Anatomogram only": "#888888",
    "HRApop only": "#D55E00",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=400)
    return parser.parse_args()


def save_all(fig: plt.Figure, output_dir: Path, stem: str, dpi: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{stem}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / f"{stem}.svg", bbox_inches="tight", facecolor="white")


def main() -> None:
    args = arguments()
    selected = pd.read_csv(args.tables_dir / "selected_ct_terms.csv", dtype={"cell_id": str})
    counts = pd.read_csv(args.tables_dir / "selected_ct_source_counts.csv", dtype={"cell_id": str})
    unique_counts = pd.read_csv(args.tables_dir / "unique_ct_counts.csv")

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    fig = plt.figure(figsize=(17.5, 10.5), constrained_layout=False)
    grid = fig.add_gridspec(2, 4, height_ratios=(2.2, 1.0), hspace=0.58, wspace=0.22)
    axes = [fig.add_subplot(grid[0, index]) for index in range(4)]

    for index, (axis, organ) in enumerate(zip(axes, ORGAN_ORDER)):
        terms = selected.loc[selected["organ_label"].eq(organ)].copy()
        terms["category"] = pd.Categorical(terms["category"], CATEGORY_ORDER, ordered=True)
        terms = terms.sort_values(["category", "category_rank"], kind="stable")

        positions: dict[str, float] = {}
        category_ranges: dict[str, tuple[float, float]] = {}
        current = 0.0
        for category in CATEGORY_ORDER:
            ids = terms.loc[terms["category"].eq(category), "cell_id"].tolist()
            start = current - 0.5
            for cell_id in ids:
                positions[cell_id] = current
                current += 1.0
            end = current - 0.5
            if ids:
                category_ranges[category] = (start, end)
                current += 0.75

        for category, (start, end) in category_ranges.items():
            axis.axvspan(start, end, color=CATEGORY_BACKGROUNDS[category], zorder=0)
            axis.text(
                (start + end) / 2,
                1.018,
                category.replace(" ", "\n") if category != "Shared" else category,
                ha="center",
                va="bottom",
                transform=axis.get_xaxis_transform(),
                fontsize=7.5,
                fontweight="bold",
                color="#404040",
                linespacing=0.92,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 1.2},
            )

        width = 0.15
        offsets = (np.arange(len(METHOD_ORDER)) - (len(METHOD_ORDER) - 1) / 2) * width
        organ_counts = counts.loc[counts["organ_label"].eq(organ)]
        for offset, method in zip(offsets, METHOD_ORDER):
            subset = organ_counts.loc[organ_counts["annotation_method"].eq(method)]
            if subset.empty:
                continue
            xs = [positions[cell_id] + offset for cell_id in subset["cell_id"]]
            axis.bar(
                xs,
                subset["cell_count"],
                width=width,
                color=METHOD_COLORS[method],
                edgecolor="white",
                linewidth=0.35,
                label=METHOD_LABELS[method],
                zorder=3,
            )

        accession_values = terms["accession"].dropna().unique()
        accession = accession_values[0] if len(accession_values) else ""
        axis.set_title(
            f"D{index + 1}: {organ}\n{accession}",
            fontweight="bold",
            y=1.115,
            pad=0,
            linespacing=0.92,
        )
        axis.set_yscale("log")
        axis.grid(axis="y", color="#C8D2D9", alpha=0.75, linewidth=0.6, zorder=1)
        axis.set_axisbelow(True)
        axis.set_xticks([positions[cell_id] for cell_id in terms["cell_id"]])
        axis.set_xticklabels(terms["cell_id"], rotation=90, ha="center")
        axis.set_xlabel("Cell Ontology term")
        if index == 0:
            axis.set_ylabel("Number of cells (log scale)")
        else:
            axis.tick_params(axis="y", labelleft=False)

    legend_handles = [Patch(color=METHOD_COLORS[m], label=METHOD_LABELS[m]) for m in METHOD_ORDER]
    fig.legend(
        handles=legend_handles,
        title="Annotation source",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.925),
        ncol=5,
        frameon=False,
    )

    bottom = fig.add_subplot(grid[1, :])
    pivot = (
        unique_counts.pivot(index="organ_label", columns="category", values="unique_ct_count")
        .reindex(index=ORGAN_ORDER, columns=CATEGORY_ORDER)
        .fillna(0)
    )
    x = np.arange(len(ORGAN_ORDER))
    bar_width = 0.22
    for offset_index, category in enumerate(CATEGORY_ORDER):
        values = pivot[category].to_numpy(dtype=float)
        bars = bottom.bar(
            x + (offset_index - 1) * bar_width,
            values,
            width=bar_width,
            color=CATEGORY_COLORS[category],
            label=category,
        )
        bottom.bar_label(bars, labels=[f"{int(v)}" for v in values], padding=3, fontsize=8)
    bottom.set_xticks(x)
    bottom.set_xticklabels([f"D{i + 1}\n{organ}" for i, organ in enumerate(ORGAN_ORDER)])
    bottom.set_ylabel("Number of unique CL terms")
    bottom.set_xlabel("Dataset")
    bottom.set_title("Unique cell-type representation by dataset", fontweight="bold", pad=12)
    bottom.grid(axis="y", color="#C8D2D9", alpha=0.75, linewidth=0.6)
    bottom.set_axisbelow(True)
    bottom.legend(loc="upper center", bbox_to_anchor=(0.5, 1.08), ncol=3, frameon=False)

    fig.suptitle(
        "Comparison of cell types in Anatomogram and HRApop",
        fontsize=16,
        fontweight="bold",
        y=0.992,
    )
    fig.text(0.012, 0.80, "A", fontsize=16, fontweight="bold")
    fig.text(0.012, 0.36, "B", fontsize=16, fontweight="bold")
    fig.text(
        0.5,
        0.012,
        "Panel A displays up to four high-count CL terms per category and dataset; Panel B uses all valid CL terms.",
        ha="center",
        fontsize=8,
        color="#555555",
    )
    fig.subplots_adjust(left=0.065, right=0.99, top=0.76, bottom=0.07)
    save_all(fig, args.output_dir, "task_01_anatomogram_vs_hrapop", args.dpi)
    plt.close(fig)


if __name__ == "__main__":
    main()
