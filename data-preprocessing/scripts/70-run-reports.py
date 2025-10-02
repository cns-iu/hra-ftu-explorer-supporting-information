from shared import *

# Make folder for reports
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)  # create the folder if it doesn't exist


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
    # FTU name | organ name | #CTs in illustration | #CTs in HRApop – unique to colliding AS | #CTs in iFTU – unique to FTU

    # Turn data into a data frame and keep relevant columns
    df = pd.DataFrame(data)[
        ["iri", "organ_label", "cell_types_in_illustration", "cell_types_in_ftu_only"]
    ]

    # Transform values as needed
    df["iri"] = df["iri"].apply(lambda iri: iri.split("/")[len(iri.split("/")) - 1])
    df["cell_types_in_illustration"] = df["cell_types_in_illustration"].apply(len)
    df["cell_types_in_ftu_only"] = df["cell_types_in_ftu_only"].apply(len)

    # Rename column
    df = df.rename(columns={"cell_types_in_ftu_only": "#CTs in iFTU – unique to FTU"})

    # Add columns as placeholders
    df["#CTs in HRApop – unique to colliding AS"] = "TBD"

    # Print result
    pprint(df)

    # Export results
    df.to_csv(f"{REPORTS_DIR}/{file_name}.csv", index=False)
    print(f"File successfully saved to {REPORTS_DIR}")


def main():
    # Driver code

    generate_ftu_report()


if __name__ == "__main__":
    main()
