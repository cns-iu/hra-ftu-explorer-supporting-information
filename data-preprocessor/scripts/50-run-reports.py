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

    # Organ labels come in mixed case from the source data (e.g., "kidney", "Small Intestine")
    df["organ_label"] = df["organ_label"].str.title()
    df = df.rename(
        columns={
            "ftu": "FTU",
            "organ_label": "Organ label",
            "cell_types_illustration": "Cell types in illustration",
            "cell_types_asctb": "Cell types in ASCT+B",
            "cell_types_exclusive": "Cell types exclusive",
        }
    )

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


def load_ftu_explorer_cell_counts() -> pd.DataFrame:
    """One row per (dataset, FTU, CT) shown in the FTU Explorer, with the CT's cell count in that dataset.
    Uses the same rules as 40/41: only datasets in FTU_TO_DATASETS, the preferred annotation tool,
    CTs exclusive to the FTU, and CTs with expression data"""

    # Written by 40: exactly the datasets listed in the FTU Explorer
    with open(FTU_TO_DATASETS, "r", encoding="utf-8") as f:
        ftu_to_datasets = json.load(f)

    exclusive_cts_by_ftu = load_exclusive_cts_by_ftu()

    dataset_to_ftus = defaultdict(set)
    for ftu_purl, dataset_ids in ftu_to_datasets.items():
        for dataset_id in dataset_ids:
            dataset_to_ftus[dataset_id].add(ftu_purl)

    rows = []
    for obj in iterate_preferred_cell_summaries():
        dataset_id = obj["cell_source"]
        for ftu in sorted(dataset_to_ftus.get(dataset_id, set())):
            allowed_cts = exclusive_cts_by_ftu.get(ftu, set())
            for summary in obj.get("summary", []):
                ct = get_id_from_iri(summary["cell_id"])
                # Same as 40/41: skip CTs whose gene_expr is empty or the string "[]"
                if (
                    ct in allowed_cts
                    and isinstance(summary.get("gene_expr"), list)
                    and summary["gene_expr"]
                ):
                    rows.append(
                        {
                            "dataset_id": dataset_id,
                            "annotation_method": obj["annotation_method"],
                            "ftu": ftu.rsplit("/", 1)[-1],
                            "cell_id": ct,
                            "cell_label": summary["cell_label"],
                            "count": summary["count"],
                        }
                    )
    return pd.DataFrame(rows)


def report_small_datasets(cell_counts: pd.DataFrame, threshold: int = 100):
    """Saves a CSV of the datasets shown in the FTU Explorer with fewer than threshold cells,
    counting only the cells 41 writes for them (see load_ftu_explorer_cell_counts). A CT exclusive
    to several FTUs (e.g., the nephron and a loop of Henle inside it) is counted once"""

    per_ct = cell_counts.drop_duplicates(["dataset_id", "cell_id"])
    df = per_ct.groupby(["dataset_id", "annotation_method"], as_index=False).agg(
        cell_count_in_ftu_explorer=("count", "sum"),
        cell_types=("cell_id", lambda ids: ";".join(sorted(ids))),
    )
    ftus = cell_counts.groupby("dataset_id")["ftu"].agg(lambda f: ";".join(sorted(set(f))))
    df.insert(2, "ftus", df["dataset_id"].map(ftus))
    metadata = load_dataset_metadata().drop_duplicates("dataset_id")[
        ["dataset_id", "organ", "consortium_name", "dataset_cell_count", "publication"]
    ]
    df = df.merge(metadata, on="dataset_id", how="left")

    small = df[df["cell_count_in_ftu_explorer"] < threshold].sort_values(
        "cell_count_in_ftu_explorer"
    )
    print(
        f"{len(small)} of {len(df)} datasets in the FTU Explorer have fewer than {threshold} cells"
    )
    pprint(small[["dataset_id", "ftus", "cell_count_in_ftu_explorer"]])

    small.to_csv(f"{REPORTS_DIR}/datasets_under_{threshold}_cells.csv", index=False)
    print(f"File successfully saved to {REPORTS_DIR}")


def load_cell_counts_without_min_cells_filter() -> pd.DataFrame:
    """Like load_ftu_explorer_cell_counts, but before MIN_CELLS_PER_CELL_TYPE is applied: the datasets
    and CTs 40/41 would show without that rule. Rebuilds the dataset -> FTU mapping as 40 does, because
    FTU_TO_DATASETS no longer lists datasets whose CTs were all too small. Keeps CTs with an empty
    gene list, because 41 wrote those (they all have 1 cell, so the rule now drops them)"""

    exclusive_cts_by_ftu = load_exclusive_cts_by_ftu()
    objs = list(iterate_preferred_cell_summaries(min_cells=0))
    cts_by_dataset = defaultdict(set)
    for obj in objs:
        cts_by_dataset[obj["cell_source"]].update(
            get_id_from_iri(s["cell_id"])
            for s in obj.get("summary", [])
            if isinstance(s.get("gene_expr"), list) and s["gene_expr"]
        )

    dataset_to_ftus = defaultdict(set)
    for dataset_id, matches in load_filtered_dataset_metadata().items():
        for match in matches:
            ct = get_id_from_iri(match["ct_iri"])
            if ct in cts_by_dataset[dataset_id] and ct in exclusive_cts_by_ftu.get(match["ftu_purl"], set()):
                dataset_to_ftus[dataset_id].add(match["ftu_purl"])

    rows = []
    for obj in objs:
        dataset_id = obj["cell_source"]
        for ftu in sorted(dataset_to_ftus.get(dataset_id, set())):
            allowed_cts = exclusive_cts_by_ftu.get(ftu, set())
            for summary in obj.get("summary", []):
                ct = get_id_from_iri(summary["cell_id"])
                if ct in allowed_cts and isinstance(summary.get("gene_expr"), list):
                    rows.append(
                        {
                            "dataset_id": dataset_id,
                            "annotation_method": obj["annotation_method"],
                            "ftu": ftu.rsplit("/", 1)[-1],
                            "cell_id": ct,
                            "cell_label": summary["cell_label"],
                            "count": summary["count"],
                        }
                    )
    return pd.DataFrame(rows)


def report_rare_cell_types_per_ftu(cell_counts: pd.DataFrame):
    """Saves a CSV with one row per dataset, FTU and CT removed from the FTU Explorer because the
    dataset has fewer than MIN_CELLS_PER_CELL_TYPE cells of that CT. dataset_removed_from_ftu is True
    when none of the dataset's CTs for that FTU are left, so the dataset isn't listed for that FTU"""

    threshold = config["MIN_CELLS_PER_CELL_TYPE"]
    all_counts = load_cell_counts_without_min_cells_filter()
    df = all_counts[all_counts["count"] < threshold].copy()
    shown = set(zip(cell_counts["dataset_id"], cell_counts["ftu"]))
    df["dataset_removed_from_ftu"] = [
        (d, f) not in shown for d, f in zip(df["dataset_id"], df["ftu"])
    ]
    df["cell_label"] = df["cell_label"].str.lower()
    df = df[
        ["ftu", "cell_id", "cell_label", "count", "dataset_id", "annotation_method", "dataset_removed_from_ftu"]
    ].sort_values(["ftu", "cell_id", "count", "dataset_id"])
    removed = df.loc[df["dataset_removed_from_ftu"], "dataset_id"]
    print(
        f"{len(df)} of {len(all_counts)} dataset/FTU/CT combinations were removed for having fewer than {threshold} cells; "
        f"{removed.nunique()} datasets lost at least one FTU, "
        f"{len(set(removed) - set(cell_counts['dataset_id']))} are gone from the FTU Explorer"
    )
    pprint(df.groupby(["ftu", "cell_label"]).size())

    df.to_csv(f"{REPORTS_DIR}/cell_types_under_{threshold}_cells_per_ftu.csv", index=False)
    print(f"File successfully saved to {REPORTS_DIR}")


def report_cells_per_cell_type_per_ftu(cell_counts: pd.DataFrame):
    """Saves a CSV with one row per FTU and CT shown in the FTU Explorer: the number of cells
    summed over all of the FTU's datasets, and how many datasets have that CT"""

    df = (
        cell_counts.groupby(["ftu", "cell_id"], as_index=False)
        .agg(
            # Labels can differ in case between tools, so take the lowercased first one, like 41
            cell_label=("cell_label", lambda labels: labels.iloc[0].lower()),
            cell_count=("count", "sum"),
            dataset_count=("dataset_id", "nunique"),
        )
        .sort_values(["ftu", "cell_count"], ascending=[True, False])
    )
    pprint(df)

    df.to_csv(f"{REPORTS_DIR}/cells_per_cell_type_per_ftu.csv", index=False)
    print(f"File successfully saved to {REPORTS_DIR}")


def report_totals_per_ftu(cell_counts: pd.DataFrame):
    """Saves ftu_explorer_totals_per_ftu.csv (all sources, with overall and per-source columns) and one CSV
    per source in CELL_SUMMARY_SOURCES (ftu_explorer_totals_per_ftu_<source>.csv, only FTUs with datasets
    from that source). Each has one row per FTU and a total row: the number of datasets, their full cell
    count (Cells in datasets) and the cells 41 writes for them (Cells in FTU Explorer, see
    load_ftu_explorer_cell_counts). A dataset can be in several FTUs and a CT exclusive to several FTUs
    (e.g., the nephron and a loop of Henle inside it), so the total row counts each dataset and each
    dataset's CT once and is less than the sum of the FTU rows"""

    # A dataset can be in several sources' metadata CSVs, but only one source contributes its cells
    source_by_dataset = {}
    for source in CELL_SUMMARY_SOURCES:
        with open(source["filtered_dataset_metadata"], "r", encoding="utf-8") as f:
            for dataset_id in json.load(f):
                source_by_dataset.setdefault(dataset_id, source["name"])

    metadata = load_dataset_metadata()[["dataset_id", "dataset_cell_count"]]
    df = cell_counts.merge(metadata, on="dataset_id", how="left")
    df["dataset_cell_count"] = pd.to_numeric(df["dataset_cell_count"], errors="coerce")
    df["source"] = df["dataset_id"].map(source_by_dataset)

    # Sentence-case headers for the manuscript; per-source columns get the source name in parentheses
    def totals(df, source_name=None):
        suffix = f" ({source_name})" if source_name else ""
        return {
            f"Datasets{suffix}": df["dataset_id"].nunique(),
            f"Cells in datasets{suffix}": int(df.drop_duplicates("dataset_id")["dataset_cell_count"].sum()),
            f"Cells in FTU Explorer{suffix}": int(df.drop_duplicates(["dataset_id", "cell_id"])["count"].sum()),
        }

    def save(report, filename, title):
        # Thousands separators for the manuscript (pandas quotes these cells in the CSV)
        for column in report.columns[1:]:
            report[column] = report[column].map("{:,}".format)
        print(f"\n{title}")
        print(report.to_string(index=False))
        report.to_csv(f"{REPORTS_DIR}/{filename}", index=False)
        print(f"{filename} successfully saved to {REPORTS_DIR}")

    # All sources in one table: overall and per-source columns
    def row_all_sources(ftu, df):
        result = {"FTU": ftu, **totals(df)}
        for source in CELL_SUMMARY_SOURCES:
            result.update(totals(df[df["source"] == source["name"]], source["name"]))
        return result

    save(
        pd.DataFrame(
            [row_all_sources(ftu, group) for ftu, group in df.groupby("ftu")]
            + [row_all_sources("Total", df)]
        ),
        "ftu_explorer_totals_per_ftu.csv",
        "All sources",
    )

    # One table per source, only FTUs with datasets from that source
    for source in CELL_SUMMARY_SOURCES:
        source_df = df[df["source"] == source["name"]]
        save(
            pd.DataFrame(
                [{"FTU": ftu, **totals(group)} for ftu, group in source_df.groupby("ftu")]
                + [{"FTU": "Total", **totals(source_df)}]
            ),
            "ftu_explorer_totals_per_ftu_" + source["name"].lower().replace(" ", "_") + ".csv",
            source["name"],
        )


def report_ftu_funnel(cell_counts: pd.DataFrame):
    """Saves ftu_funnel_per_ftu.csv: one row per FTU (and a total row) going from all datasets of the FTU's
    organ to what the FTU Explorer shows: datasets from the organ (every source's datasets of interest, minus
    excluded datasets) and their cells, CTs in the illustration, CTs exclusive to the FTU, and the datasets and
    cells shown in the FTU Explorer (see load_ftu_explorer_cell_counts). The oral cavity datasets count for
    every mouth FTU, because their organ is mouth. The total row counts each dataset and CT once"""

    datasets_of_interest_files = [
        DATASETS_OF_INTEREST,
        ANATOMOGRAM_DATASETS_OF_INTEREST,
        ORAL_CAVITY_DATASETS_OF_INTEREST,
    ]
    datasets_by_organ = defaultdict(set)
    for path in datasets_of_interest_files:
        for entry in load_json(path)["datasets_of_interest"]:
            for dataset_id, organ_id in entry.items():
                if not is_excluded_dataset(dataset_id):
                    datasets_by_organ[organ_id].add(dataset_id)

    metadata = load_dataset_metadata()
    cells_by_dataset = (
        pd.to_numeric(metadata["dataset_cell_count"], errors="coerce")
        .fillna(0)
        .astype(int)
        .set_axis(metadata["dataset_id"])
        .to_dict()
    )
    missing = set().union(*datasets_by_organ.values()) - set(cells_by_dataset)
    if missing:
        print(f"⚠️ {len(missing)} datasets of interest have no cell count in the metadata")

    with open(CELL_TYPES_IN_FTUS, "r", encoding="utf-8") as f:
        organ_by_ftu = {
            ftu["ftu_purl"].rstrip("/").split("/")[-1]: ftu["organ_id_short"]
            for ftu in json.load(f).values()
        }
    ct_sets = load_ct_sets_per_ftu()

    def row(ftu, organ_datasets, illustration, exclusive, shown):
        return {
            "FTU": ftu,
            "Datasets from organ": len(organ_datasets),
            "Cells in datasets from organ": sum(cells_by_dataset.get(d, 0) for d in organ_datasets),
            "Cell types in illustration": len(illustration),
            "Cell types exclusive": len(exclusive),
            "Datasets in FTU Explorer": shown["dataset_id"].nunique(),
            "Cells in FTU Explorer": int(shown.drop_duplicates(["dataset_id", "cell_id"])["count"].sum()),
        }

    rows = [
        row(
            ftu.ftu,
            datasets_by_organ.get(organ_by_ftu[ftu.ftu], set()),
            ftu.illustration,
            ftu.exclusive,
            cell_counts[cell_counts["ftu"] == ftu.ftu],
        )
        for ftu in ct_sets.itertuples(index=False)
    ]
    rows.append(
        row(
            "Total",
            set().union(*(datasets_by_organ.get(o, set()) for o in set(organ_by_ftu.values()))),
            set().union(*ct_sets["illustration"]),
            set().union(*ct_sets["exclusive"]),
            cell_counts,
        )
    )
    report = pd.DataFrame(rows)
    print(report.to_string(index=False))

    # Thousands separators for the manuscript (pandas quotes these cells in the CSV)
    for column in report.columns[1:]:
        report[column] = report[column].map("{:,}".format)
    report.to_csv(f"{REPORTS_DIR}/ftu_funnel_per_ftu.csv", index=False)
    print(f"File successfully saved to {REPORTS_DIR}")


def main():
    # Driver code

    # generate_ftu_report()

    get_unique_cts_for_colliding_as()
    generate_ftu_report()
    visualize_intersections()
    visualize_bar_graph()
    cell_counts = load_ftu_explorer_cell_counts()
    report_small_datasets(cell_counts)
    report_rare_cell_types_per_ftu(cell_counts)
    report_cells_per_cell_type_per_ftu(cell_counts)
    report_totals_per_ftu(cell_counts)
    report_ftu_funnel(cell_counts)


if __name__ == "__main__":
    main()
