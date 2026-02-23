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


def main():
    # Driver code

    # generate_ftu_report()

    get_unique_cts_for_colliding_as()
    generate_ftu_report()
    visualize_intersections()


if __name__ == "__main__":
    main()
