#!/usr/bin/env python3
"""Generate the Task 2 strict and ontology-aware manuscript figures."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch, Rectangle


METHOD_ORDER = ("CellTypist", "Azimuth", "popV", "FR-Match")
ORGAN_ORDER = ("Kidney", "Liver", "Lung", "Pancreas")
RELATIONSHIPS = ("Exact", "CTann narrower", "CTann broader", "Different branch", "Unmapped")
RELATIONSHIP_COLUMNS = {
    "Exact": "exact_fraction",
    "CTann narrower": "ctann_narrower_fraction",
    "CTann broader": "ctann_broader_fraction",
    "Different branch": "different_branch_fraction",
    "Unmapped": "unmapped_fraction",
}
RELATIONSHIP_COLORS = {
    "Exact": "#0072B2",
    "CTann narrower": "#56B4E9",
    "CTann broader": "#009E73",
    "Different branch": "#D55E00",
    "Unmapped": "#999999",
}
HEATMAP_CMAP = LinearSegmentedColormap.from_list("agreement", ["#F7FBFF", "#56B4E9", "#005A8D"])


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-dir", required=True, type=Path)
    parser.add_argument("--ontology-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=400)
    return parser.parse_args()


def save_all(fig: plt.Figure, output_dir: Path, stem: str, dpi: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{stem}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / f"{stem}.svg", bbox_inches="tight", facecolor="white")


def heatmap_panel(
    axis: plt.Axes,
    values: pd.DataFrame,
    counts: pd.DataFrame,
    statuses: pd.DataFrame,
    title: str,
) -> None:
    matrix = values.reindex(index=METHOD_ORDER, columns=ORGAN_ORDER).to_numpy(dtype=float)
    masked = np.ma.masked_invalid(matrix)
    axis.imshow(masked, vmin=0, vmax=1, cmap=HEATMAP_CMAP, aspect="auto")
    axis.set_xticks(np.arange(len(ORGAN_ORDER)))
    axis.set_xticklabels(ORGAN_ORDER)
    axis.set_yticks(np.arange(len(METHOD_ORDER)))
    axis.set_yticklabels(METHOD_ORDER)
    axis.set_title(title, fontweight="bold", pad=12)

    count_matrix = counts.reindex(index=METHOD_ORDER, columns=ORGAN_ORDER)
    status_matrix = statuses.reindex(index=METHOD_ORDER, columns=ORGAN_ORDER)
    for row in range(len(METHOD_ORDER)):
        for column in range(len(ORGAN_ORDER)):
            value = matrix[row, column]
            status = status_matrix.iloc[row, column]
            if np.isfinite(value):
                n = int(count_matrix.iloc[row, column])
                color = "white" if value >= 0.48 else "#202020"
                axis.text(column, row, f"{value:.1%}\nn={n:,}", ha="center", va="center", color=color, fontsize=8)
            else:
                axis.add_patch(
                    Rectangle(
                        (column - 0.5, row - 0.5),
                        1,
                        1,
                        facecolor="#EEEEEE",
                        edgecolor="white",
                        hatch="///" if status == "unavailable_identifier_crosswalk" else None,
                    )
                )
                label = "No barcode\ncrosswalk" if status == "unavailable_identifier_crosswalk" else "Not run"
                axis.text(column, row, label, ha="center", va="center", fontsize=7, color="#555555")
    axis.set_xticks(np.arange(-0.5, len(ORGAN_ORDER), 1), minor=True)
    axis.set_yticks(np.arange(-0.5, len(METHOD_ORDER), 1), minor=True)
    axis.grid(which="minor", color="white", linewidth=2)
    axis.tick_params(which="minor", bottom=False, left=False)
    for spine in axis.spines.values():
        spine.set_visible(False)


def main() -> None:
    args = arguments()
    strict = pd.read_csv(args.strict_dir / "strict_by_organ_method.csv")
    ontology_overall = pd.read_csv(args.ontology_dir / "ontology_overall_by_method.csv")
    ontology_organ = pd.read_csv(args.ontology_dir / "ontology_by_organ_method.csv")

    exact = strict.pivot(index="method_label", columns="organ_label", values="exact_agreement")
    eligible = strict.pivot(index="method_label", columns="organ_label", values="strict_eligible_cells")
    status = strict.pivot(index="method_label", columns="organ_label", values="status")
    compatible = ontology_organ.pivot(
        index="method_label", columns="organ_label", values="ontology_compatible_fraction"
    )
    compatible_n = ontology_organ.pivot(
        index="method_label", columns="organ_label", values="eligible_paired_cells"
    )

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    fig = plt.figure(figsize=(14.5, 9.5))
    grid = fig.add_gridspec(2, 2, height_ratios=(1.05, 1.0), hspace=0.4, wspace=0.34)
    axis_a = fig.add_subplot(grid[0, 0])
    axis_c = fig.add_subplot(grid[0, 1])
    axis_b = fig.add_subplot(grid[1, :])

    heatmap_panel(axis_a, exact, eligible, status, "Strict exact CL-ID agreement")
    compatible_status = status.copy()
    heatmap_panel(axis_c, compatible, compatible_n, compatible_status, "Ontology-compatible agreement")

    overall = ontology_overall.set_index("method_label").reindex(METHOD_ORDER)
    y = np.arange(len(METHOD_ORDER))
    left = np.zeros(len(METHOD_ORDER), dtype=float)
    for relationship in RELATIONSHIPS:
        column = RELATIONSHIP_COLUMNS[relationship]
        values = overall[column].fillna(0).to_numpy(dtype=float)
        axis_b.barh(
            y,
            values,
            left=left,
            color=RELATIONSHIP_COLORS[relationship],
            edgecolor="white",
            linewidth=0.7,
            label=relationship,
        )
        for row, (start, value) in enumerate(zip(left, values)):
            if value >= 0.065:
                axis_b.text(
                    start + value / 2,
                    row,
                    f"{value:.0%}",
                    ha="center",
                    va="center",
                    color="white" if relationship != "CTann narrower" else "#202020",
                    fontsize=8,
                    fontweight="bold",
                )
        left += values

    fr_row = METHOD_ORDER.index("FR-Match")
    axis_b.add_patch(Rectangle((0, fr_row - 0.34), 1, 0.68, facecolor="#EEEEEE", hatch="///", edgecolor="#BBBBBB"))
    axis_b.text(0.5, fr_row, "NA - no barcode crosswalk", ha="center", va="center", color="#555555")
    axis_b.set_yticks(y)
    axis_b.set_yticklabels(METHOD_ORDER)
    axis_b.invert_yaxis()
    axis_b.set_xlim(0, 1)
    axis_b.set_xticks(np.linspace(0, 1, 5))
    axis_b.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    axis_b.set_xlabel("Percentage of eligible paired cells")
    axis_b.set_title("Supertree relationship between author and CTann annotations", fontweight="bold", pad=12)
    axis_b.grid(axis="x", color="#D5DDE2", linewidth=0.7)
    axis_b.set_axisbelow(True)
    handles = [Patch(color=RELATIONSHIP_COLORS[r], label=r) for r in RELATIONSHIPS]
    axis_b.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=5, frameon=False)

    fig.suptitle("Author annotations versus CTann cell-type annotations", fontsize=16, fontweight="bold", y=0.98)
    fig.text(0.015, 0.925, "A", fontsize=16, fontweight="bold")
    fig.text(0.505, 0.925, "C", fontsize=16, fontweight="bold")
    fig.text(0.015, 0.465, "B", fontsize=16, fontweight="bold")
    fig.text(
        0.5,
        0.015,
        "Denominator: paired cells with valid CL identifiers on both sides. Valid IDs absent from the supplied supertree are retained as Unmapped.",
        ha="center",
        fontsize=8,
        color="#555555",
    )
    fig.subplots_adjust(left=0.1, right=0.98, top=0.91, bottom=0.12)
    save_all(fig, args.output_dir, "task_02_author_ctann_supertree", args.dpi)
    plt.close(fig)

    # Supplementary: organ-specific ontology relationship composition.
    supplemental = ontology_organ.copy()
    supplemental["plot_label"] = supplemental["method_label"] + " - " + supplemental["organ_label"]
    method_rank = {value: index for index, value in enumerate(METHOD_ORDER)}
    organ_rank = {value: index for index, value in enumerate(ORGAN_ORDER)}
    supplemental["method_rank"] = supplemental["method_label"].map(method_rank)
    supplemental["organ_rank"] = supplemental["organ_label"].map(organ_rank)
    supplemental = supplemental.sort_values(["method_rank", "organ_rank"])

    fig_si, axis = plt.subplots(figsize=(11.5, 7.0))
    y = np.arange(len(supplemental))
    left = np.zeros(len(supplemental), dtype=float)
    for relationship in RELATIONSHIPS:
        values = supplemental[RELATIONSHIP_COLUMNS[relationship]].to_numpy(dtype=float)
        axis.barh(y, values, left=left, color=RELATIONSHIP_COLORS[relationship], edgecolor="white", linewidth=0.5)
        left += values
    axis.set_yticks(y)
    axis.set_yticklabels(
        [f"{label}  (n={n:,})" for label, n in zip(supplemental["plot_label"], supplemental["eligible_paired_cells"])]
    )
    axis.invert_yaxis()
    axis.set_xlim(0, 1)
    axis.set_xticks(np.linspace(0, 1, 5))
    axis.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    axis.set_xlabel("Percentage of eligible paired cells")
    axis.set_title("Organ-specific author-CTann supertree relationships", fontsize=14, fontweight="bold")
    axis.grid(axis="x", color="#D5DDE2", linewidth=0.7)
    axis.set_axisbelow(True)
    axis.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=5, frameon=False)
    fig_si.subplots_adjust(left=0.28, right=0.98, top=0.91, bottom=0.15)
    save_all(fig_si, args.output_dir, "task_02_supplementary_relationships", args.dpi)
    plt.close(fig_si)


if __name__ == "__main__":
    main()
