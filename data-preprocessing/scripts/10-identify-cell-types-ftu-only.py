from shared import *


def get_organs_with_ftus():
    """Retrieves a list of FTUs and their parts via the HRA API and a SPARQL query

    Returns:
        organs_with_ftus (list): A list of organs with their FTUs
    """

    df = get_csv_pandas("https://apps.humanatlas.io/api/grlc/hra/2d-ftu-parts.csv")

    # Loop through df and identify organs and their FTUs
    organs_with_ftus = []

    for (organ_label, organ_id), group in df.groupby(["organ_label", "organ_iri"]):
        organ_dict = {
            "organ_label": organ_label,
            "organ_id": organ_id,
            "ftu": group[["ftu_iri", "ftu_digital_object"]]
            .drop_duplicates()
            .to_dict(orient="records"),  # list of dicts
        }
        organs_with_ftus.append(organ_dict)

    return organs_with_ftus


def compile_cell_types_per_ftu(organs_with_ftus: list):
    """
    Compiles a list of cell types associated with FTUs across a set of organs, by retrieving and parsing metadata from DO URLs.

    For each FTU in the provided organs, this function:
      - Queries the HRA KG using the FTU's PURL.
      - Extracts organ and FTU metadata (organ label, organ ID, representation, IRI).
      - Collects all unique cell types present in the FTU illustration.
      - Differentiates between cell types present in the FTU illustration and those
        that occur only within the FTU.

    Args:
        organs_with_ftus (list): A list of dictionaries, where each dictionary represents
            an organ and must contain:
                - "organ_label" (str): Human-readable organ name.
                - "organ_id" (str): Unique identifier for the organ.
                - "ftu" (list): A list of FTU dictionaries, each containing:
                    - "ftu_digital_object" (str): URL (PURL) to the FTU's digital object.

    Returns:
        list: A list of dictionaries, one per FTU, each containing:
            - "organ_label" (str): Organ name.
            - "organ_id" (str): Organ identifier.
            - "representation_of" (str): Ontology term or structure represented by the FTU.
            - "iri" (str): IRI of the FTU digital object.
            - "cell_types_in_illustration" (set of tuples): Set of unique (node_group, representation_of)
              pairs representing cell types present in the FTU illustration.
            - "cell_types_in_ftu_only" (set of tuples): Set of unique cell types found exclusively
              in the FTU and not in other anatomical structures.

    Notes:
        - Cell types are stored in sets of tuples for uniqueness and hashability.
        - Prints progress messages when querying each FTU PURL.
    """

    # Initialize resulting list of dictionaries to capture FTUs and the cell types inside them
    ftu_cell_types = []

    # Get data for all FTU illustrations
    for organ in organs_with_ftus:
        for do in organ["ftu"]:

            # Get the PURL for the FTU
            url = do["ftu_digital_object"]

            # Make a web request to the PURL
            print(f"Now calling HRA KG to get data for DO with PURL: {url}.")
            do_json = requests.get(url, headers=accept_json).json()

            # Extract relevant metadata from the response
            data_to_add = {
                "asctb_purl": "",
                "organ_label": organ["organ_label"],
                "organ_id": organ["organ_id"],
                "organ_id_short": organ["organ_id"].split("/")[-1].replace("_", ":"),
                "representation_of": do_json["data"][0]["representation_of"],
                "iri": do_json["iri"],
                "cell_types_in_illustration": [],  # Captures cell types in FTU illustration
                "cell_types_in_ftu_only": [],  # Captures cell types that occur only in the FTU and not any other anatomical structures
            }

            # Create listing of unique cell types in the FTU illustration
            for node in do_json["data"][0]["illustration_node"]:
                existing = {
                    d.get("representation_of")
                    for d in data_to_add["cell_types_in_illustration"]
                }
                if node['representation_of'] not in existing:
                    data_to_add["cell_types_in_illustration"].append(
                        {
                            "node_group": node["node_group"],
                            "representation_of": node["representation_of"],
                        }  # a dict to capture cell types per FTU illustration. Tuples are hashable.
                    )

            ftu_cell_types.append(data_to_add)

    print()

    return ftu_cell_types


def validate_against_asctb(ftu_cell_types: list):
    """Takes in a list of dictioanries describing FTUs, their metadata, and the cell types in them, then validates them against the AS-CT records in the ASCT+B tables

    Args:
        ftu_cell_types (list): A list of dictioanries describing FTUs

    Returns:
        ftu_cell_types_validated: The same list of dictionaries with additional values
    """

    pprint(ftu_cell_types)
    print()

    # collect PURLs for ASCT+B tables (alt: use https://lod.humanatlas.io/asct-b)
    hra_do_list = requests.get(
        "https://apps.humanatlas.io/api/kg/digital-objects", headers=accept_json
    ).json()

    # Compile list of nique organs covered by FTUs
    unique_organs = list(
        {entry["organ_id"].split("/")[-1].replace("_", ":") for entry in ftu_cell_types}
    )
    print("Unique organs covered by FTU illustrations:")
    pprint(unique_organs)
    print()

    # Get PURLs for organs with FTUs
    asctb_purls = set()
    for do in hra_do_list["@graph"]:
        if do["doType"] == "asct-b":

            if "organIds" in do:
                last_token = [
                    id.split("/")[-1].replace("_", ":") for id in do["organIds"]
                ]

                if any(token in unique_organs for token in last_token):
                    purl = do["@id"].replace("lod", "purl")
                    asctb_purls.add(purl)

    # manually removing anatomical-systems for now
    asctb_purls.remove("https://purl.humanatlas.io/asct-b/anatomical-systems")

    print("PURLs for ASCT+B tables:")
    pprint(asctb_purls)
    print()

    # download ASCT+B table data and keep 'records' (list of dicts with AS-CT-B records + references)
    for purl in asctb_purls:
        asctb_table = requests.get(purl, headers=accept_json).json()
        print("========================")
        print(
            f"{asctb_table['iri']} has {len(asctb_table['data']['asctb_record'])} records."
        )
        print()
        # find FTUs for that organ

        for ftu in ftu_cell_types:
            target = ftu["organ_id_short"]
            if any(
                item["id"] == target
                for item in asctb_table["data"]["anatomical_structures"]
            ):
                ftu["asctb_purl"] = asctb_table["iri"]
                pprint(ftu)
                print()

                # Set certain Uberon IDs to be ignored
                ignore_uberon_ids = [
                    ftu["organ_id_short"],  # organ ID
                    ftu["representation_of"],  # FTU ID
                    "UBERON:0013702",  # body proper
                    "FMA:29733",  # General anatomical term
                    "FMA:62955",  # FMA anatomical structure
                    "UBERON:0001062",  # UBERON anatomical structure
                ]

                # Loop through cell types in FTU illustration and check if they are associated with only the FTU or one of its children in the ASCT+B table
                for cell_type_ftu in ftu["cell_types_in_illustration"]:
                    pprint(f"Now checking {cell_type_ftu}.")

                    # Set flags for checking if the cell type is only associated with the FTU in this organ
                    is_only_associated_with_ftu = True

                    # Check if the CT is associated with any other AS in the table
                    for cell_type_table in asctb_table["data"]["cell_types"]:
                        if cell_type_table["id"] == cell_type_ftu['representation_of']:
                            if "ccf_located_in" in cell_type_table:
                                other_as_ids = [
                                    item
                                    for item in cell_type_table["ccf_located_in"]
                                    if item not in ignore_uberon_ids
                                ]
                                if other_as_ids:
                                    is_only_associated_with_ftu = False
                                    print(
                                        f"{cell_type_ftu['representation_of']} was also found in:"
                                    )
                                    pprint(other_as_ids)
                                    print()
                                else:
                                    print(f"{cell_type_ftu['representation_of']} was only found in FTU")

                    if is_only_associated_with_ftu:
                        ftu["cell_types_in_ftu_only"].append(cell_type_ftu)

    with_exclusive_cts = []
    without_exclusive_cts = []

    for ftu in ftu_cell_types:
        # identify exclusive and non-exclusive cell types
        (
            with_exclusive_cts
            if ftu["cell_types_in_ftu_only"]
            else without_exclusive_cts
        ).append(ftu["iri"])

    print("FTUs with CTs unique to them:")
    print("\n".join(with_exclusive_cts))
    print()
    print("FTUs without CTs unique to them:")
    print("\n".join(without_exclusive_cts))

    with open(CELL_TYPES_IN_FTUS, "w") as f:
        json.dump(ftu_cell_types, f, indent=2)

    print(f"Saved data to {CELL_TYPES_IN_FTUS}")

    ftu_cell_types_validated = ftu_cell_types

    return ftu_cell_types_validated


def main():
    # Driver code

    # Get listing of FTUs and metadata (IRIs etc.) per organ
    organ_ftus = get_organs_with_ftus()

    # Use this listing of FTUs per organ to query the HRA KG for the cell types in the FTU illustrations
    cell_types_per_ftu = compile_cell_types_per_ftu(organ_ftus)

    # Compare the cell types in the FTUs against ASCT+B tables and capture which appear only in the FTUs and not in other AS
    cell_types_per_ftu_validated = validate_against_asctb(cell_types_per_ftu)


if __name__ == "__main__":
    main()
