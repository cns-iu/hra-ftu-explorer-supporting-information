import numpy as np

from shared import *


def get_unique_cts_for_colliding_as():
    """_summary_"""

    # Get list of organs, AS, and CTs for them from HRApop via SPARQL/HRA API
    df = get_csv_pandas(
        "https://apps.humanatlas.io/api/grlc/hra-pop/cell_types_in_anatomical_structurescts_per_as.csv"
    )

    # Get uniquecombinations of organs, AS, and cells
    df_unique = df.drop_duplicates(
        subset=["organ", "as_label", "cell_id", "cell_label"]
    )

    # Get allowed organ labels (normalized to lowercase)
    organs_with_ftus_labels = {o["organ_label"].lower() for o in get_organs_with_ftus()}

    # Filter DataFrame by those labels
    df_filtered = df[df["organ"].str.lower().isin(organs_with_ftus_labels)]

    pprint(df_filtered)


def load_ct_sets_per_ftu() -> pd.DataFrame:
    """One row per FTU from cell-types-in-ftus.json (stage 10), with the CL CURIEs of its CTs
    in the illustration, in the ASCT+B tables, and exclusive to it"""
    with open(CELL_TYPES_IN_FTUS, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"✅ Loaded {CELL_TYPES_IN_FTUS}")

    def ct_ids(cts):
        return {ct["ct_iri"] for ct in cts if ct.get("ct_iri")}

    return pd.DataFrame(
        [
            {
                "ftu": ftu["ftu_purl"].rstrip("/").split("/")[-1],
                "organ_label": ftu["organ_label"],
                "illustration": ct_ids(ftu.get("cts_in_2d_ftu", [])),
                "asctb": ct_ids(ftu.get("cts_in_asctb", [])),
                "exclusive": ct_ids(ftu.get("cts_exclusive", [])),
            }
            for ftu in data.values()
        ]
    )


def generate_ftu_report():
    """Saves a CSV with one row per FTU: its organ and how many CTs are in its illustration,
    in the ASCT+B tables, and exclusive to it"""

    df = load_ct_sets_per_ftu()
    for column in ["illustration", "asctb", "exclusive"]:
        df[f"cell_types_{column}"] = df.pop(column).apply(len)

    pprint(df)

    df.to_csv(f"{REPORTS_DIR}/cell_types_in_ftu_report.csv", index=False)
    print(f"File successfully saved to {REPORTS_DIR}")


def visualize_intersections():
    """UpSet plot of which CTs are in each FTU's illustration and/or ASCT+B table"""

    memberships = []
    for ftu in load_ct_sets_per_ftu().itertuples(index=False):
        for ct in ftu.illustration | ftu.asctb:
            membership = []
            if ct in ftu.illustration:
                membership.append(f"Illustration|{ftu.ftu}")
            if ct in ftu.asctb:
                membership.append(f"ASCTB|{ftu.ftu}")
            memberships.append(membership)

    upset_data = from_memberships(memberships)

    fig = plt.figure(figsize=(20, 10))
    # UpSetPlot 0.9.0's own show_counts crashes with numpy 2 / matplotlib 3.10, so label the bars ourselves
    up = UpSet(upset_data, show_counts=False, subset_size="count")
    axes = up.plot(fig=fig)
    axes["intersections"].bar_label(axes["intersections"].containers[0])

    plt.title("UpSet: Illustration vs. ASCT+B per FTU", fontsize=44)
    plt.tight_layout()

    plt.savefig(os.path.join(REPORTS_DIR, "upset_cell_type_overlap.png"), dpi=300)
    plt.close()


def visualize_bar_graph():
    """Grouped bar chart (and CSV) of CTs per FTU: in the illustration, in ASCT+B, and in both"""

    df = load_ct_sets_per_ftu()
    df["illustration_count"] = df["illustration"].apply(len)
    df["asctb_count"] = df["asctb"].apply(len)
    shared = [i & a for i, a in zip(df["illustration"], df["asctb"])]
    df["shared_count"] = [len(ids) for ids in shared]
    df["shared_ids"] = [";".join(sorted(ids)) for ids in shared]

    df = df.sort_values("shared_count", ascending=False).reset_index(drop=True)
    columns = ["ftu", "illustration_count", "asctb_count", "shared_count", "shared_ids"]
    print(df[columns[:-1]].to_string(index=False))
    df[columns].to_csv(f"{REPORTS_DIR}/celltype_counts_by_ftu.csv", index=False)

    x = np.arange(len(df))
    width = 0.25

    fig, ax = plt.subplots(figsize=(max(8, len(df) * 0.5), 6))
    ax.bar(x - width, df["illustration_count"], width, label="illustration_count")
    ax.bar(x, df["asctb_count"], width, label="asctb_count")
    ax.bar(x + width, df["shared_count"], width, label="shared_count")

    ax.set_xticks(x)
    ax.set_xticklabels(df["ftu"], rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Count")
    ax.set_title("Cell types per FTU: illustration vs. ASCT+B vs. shared (CL IDs only)")
    ax.legend()
    plt.tight_layout()

    plt.savefig(f"{REPORTS_DIR}/celltype_counts_grouped_bar.png", dpi=150, bbox_inches="tight")
    plt.close()


def main():
    # Driver code

    # generate_ftu_report()

    get_unique_cts_for_colliding_as()
    generate_ftu_report()
    visualize_intersections()
    visualize_bar_graph()


if __name__ == "__main__":
    main()
