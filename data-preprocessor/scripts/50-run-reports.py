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


def generate_ftu_report():
    """
    Generate a summary report of CTs in FTUs.

    This function:
      - Loads FTU cell type data from a JSON file.
      - Extracts relevant fields (IRI, organ label, cell types in illustration, etc.).
      - Transforms list-valued fields into counts.
      - Builds a pandas DataFrame with one row per unique FTU.
      - Exports the resulting summary as a CSV file.

    The file is saved to the configured OUTPUT_DIR.
    """

    # Set file name
    file_name = "cell_types_in_ftu_report"

    # load cell types in FTUs
    with open(CELL_TYPES_IN_FTUS) as f:
        data = json.load(f)
        print(f"✅ Loaded {CELL_TYPES_IN_FTUS}")
    pprint(data)

    # Goal: make CSV with 26 rows—one per unique FTU:

    # Turn data into a data frame and keep relevant columns
    df = pd.DataFrame(data)[
        [
            "iri",
            "organ_label",
            "cell_types_in_illustration",
            "cell_types_in_asctb_ftu_column",
        ]
    ]

    # Transform values as needed

    df["iri"] = df["iri"].apply(lambda iri: iri.split("/")[len(iri.split("/")) - 1])

    df["cell_types_in_illustration"] = df["cell_types_in_illustration"].apply(len)
    df["cell_types_in_asctb_ftu_column"] = df["cell_types_in_asctb_ftu_column"].apply(
        len
    )

    # Print result
    pprint(df)

    # Export results
    df.to_csv(f"{REPORTS_DIR}/{file_name}.csv", index=False)
    print(f"File successfully saved to {REPORTS_DIR}")


def visualize_intersections():
    """_summary_"""

    # -----------------------------
    # CONFIG
    # -----------------------------
    OUT_FILE = "upset_cell_type_overlap.png"

    # os.makedirs(REPORTS_DIR, exist_ok=True)

    # -----------------------------
    # Load JSON (uploaded file)
    # -----------------------------
    with open(CELL_TYPES_IN_FTUS, "r") as f:
        data = json.load(f)

    def short_label_from_iri(iri):
        if not iri:
            return "unknown"
        path = urlsplit(iri).path
        tail = path.rstrip("/").split("/")[-1]
        return tail or iri

    memberships = []

    # -----------------------------
    # Build memberships
    # -----------------------------
    for ftu in data:
        iri = ftu.get("iri") or "unknown_iri"
        iri_short = short_label_from_iri(iri)

        set_name_illus = f"Illustration|{iri_short}"
        set_name_asctb = f"ASCTB|{iri_short}"

        illustration_ids = {
            ct.get("representation_of")
            for ct in ftu.get("cell_types_in_illustration", [])
            if ct.get("representation_of") is not None
        }

        asctb_ids = {
            ct.get("cell_id")
            for ct in ftu.get("cell_types_in_asctb_ftu_column", [])
            if ct.get("cell_id") is not None
        }

        for cid in illustration_ids | asctb_ids:
            membership = []
            if cid in illustration_ids:
                membership.append(set_name_illus)
            if cid in asctb_ids:
                membership.append(set_name_asctb)
            memberships.append(membership)

    # -----------------------------
    # Create UpSet data
    # -----------------------------
    upset_data = from_memberships(memberships)

    # -----------------------------
    # Plot
    # -----------------------------
    plt.figure(figsize=(14, 8))
    up = UpSet(upset_data, show_counts=True, subset_size="count")
    up.plot()

    plt.title("UpSet: Illustration vs ASCTB per FTU")
    plt.tight_layout()

    # -----------------------------
    # Save figure
    # -----------------------------
    out_path = os.path.join(REPORTS_DIR, OUT_FILE)
    plt.savefig(out_path, dpi=300)
    plt.close()


# print(f"Figure saved to: {out_path}")


def visualize_bar_graph():
    # requirements: pandas, matplotlib
    # run with: python myscript.py
    import json
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    # --- STEP 1: load your data ---
    # Option A: paste your JSON into a file 'data.json' and load it:
    with open(CELL_TYPES_IN_FTUS, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Option B: if you already have the Python object 'records', skip loading.

    # --- STEP 2: helper functions to extract CL: ids ---
    def extract_cl_ids_from_illustration(items):
        ids = set()
        for it in items:
            v = it.get("representation_of", "") or ""
            if isinstance(v, str) and v.startswith("CL:"):
                ids.add(v.strip())
        return ids

    def extract_cl_ids_from_asctb(items):
        ids = set()
        for it in items:
            v = it.get("cell_id", "") or ""
            if isinstance(v, str) and v.startswith("CL:"):
                ids.add(v.strip())
        return ids

    # --- STEP 3: compute counts per IRI ---
    rows = []
    for rec in records:
        iri = rec.get("iri", "<no-iri>")
        illu_ids = extract_cl_ids_from_illustration(
            rec.get("cell_types_in_illustration", [])
        )
        asctb_ids = extract_cl_ids_from_asctb(
            rec.get("cell_types_in_asctb_ftu_column", [])
        )
        shared = illu_ids.intersection(asctb_ids)
        rows.append(
            {
                "iri": iri,
                "illustration_count": len(illu_ids),
                "asctb_count": len(asctb_ids),
                "shared_count": len(shared),
                "shared_ids": ";".join(sorted(shared)),
            }
        )

    df = pd.DataFrame(rows)

    # sort rows by shared_count descending (optional)
    df = df.sort_values("shared_count", ascending=False).reset_index(drop=True)

    # --- STEP 4: show / save the table ---
    print(
        df[["iri", "illustration_count", "asctb_count", "shared_count"]].to_string(
            index=False
        )
    )
    df.to_csv("celltype_counts_by_iri.csv", index=False)  # optional export

    # --- STEP 5: grouped bar chart ---
    x = np.arange(len(df))
    width = 0.25

    fig, ax = plt.subplots(
        figsize=(max(8, len(df) * 0.5), 6)
    )  # widen figure if many IRIs
    ax.bar(x - width, df["illustration_count"], width, label="illustration_count")
    ax.bar(x, df["asctb_count"], width, label="asctb_count")
    ax.bar(x + width, df["shared_count"], width, label="shared_count")

    # create short labels by splitting on '/'
    df['iri_short'] = df['iri'].apply(lambda s: s.rstrip('/').split('/')[-1])

    ax.set_xticks(x)
    ax.set_xticklabels(df["iri_short"], rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Count")
    ax.set_title(
        "Cell-type counts per IRI: illustration vs asctb vs shared (CL: ids only)"
    )
    ax.legend()
    plt.tight_layout()

    # save file and show
    plt.savefig(f"{REPORTS_DIR}/celltype_counts_grouped_bar.png", dpi=150, bbox_inches="tight")
    plt.show()


def main():
    # Driver code

    # generate_ftu_report()

    get_unique_cts_for_colliding_as()
    generate_ftu_report()
    visualize_intersections()
    visualize_bar_graph()


if __name__ == "__main__":
    main()
