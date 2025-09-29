from shared import *

def get_organs_with_ftus():
    """Retrieves a list of FTUs and their parts via the HRA API and a SPARQL query

    Returns:
        organs_with_ftus (list): A list of organs with their FTUs
    """

    df = get_csv_pandas("https://apps.humanatlas.io/api/grlc/hra/2d-ftu-parts.csv")

    # Loop through df and identify organs and their FTUs
    organs_with_ftus = []

    for (organ_label, organ_id), group in df.groupby(['organ_label', 'organ_iri']):
        organ_dict = {
            'organ_label': organ_label,
            'organ_id': organ_id,
            'ftu': group[['ftu_iri', 'ftu_digital_object']]
            .drop_duplicates()
            .to_dict(orient="records"),  # list of dicts
        }
        organs_with_ftus.append(organ_dict)

    return organs_with_ftus


def compile_cell_types_per_ftu(organs_with_ftus:list):
    """_summary_

    Args:
        organs_with_ftus (list): _description_

    Returns:
        _type_: _description_
    """

    # Initialize resulting list of dictionaries to capture FTUs and the cell types inside them
    ftu_cell_types = []

    # Get data for all FTU illustrations
    for organ in organs_with_ftus:
        for do in organ['ftu']:

            # Get the PURL for the FTU
            url = do["ftu_digital_object"]

            # Make a web request to the PURL
            print(f"Now calling HRA KG to get data for DO with PURL: {url}.")
            print()
            do_json = requests.get(url, headers=accept_json).json()

            # Extract relevant metadata from the response
            data_to_add = {
                "organ_label": organ["organ_label"],
                "organ_id": organ["organ_id"],
                "representation_of": do_json["data"][0]["representation_of"],
                "iri": do_json["iri"],
                "cell_types_in_illustration": set(),  # note that this is a set, captures cell types in FTU illustration
                "cell_types_in_ftu_only": set(),  # note that this is also set, captures cell types that occur only in the FTU and not any other anatomical structures
            }

            # Create listing of unique cell types in the FTU illustration
            for node in do_json["data"][0]["illustration_node"]:
                data_to_add["cell_types_in_illustration"].add(
                    (node["node_group"], node["representation_of"]) # a tuple to capture cell types per FTU illustration. Tuples are hashable.
                )

            ftu_cell_types.append(data_to_add)

    return ftu_cell_types

def validate_against_asctb(ftu_cell_types:list):
    """_summary_

    Args:
        ftu_cell_types (list): _description_

    Returns:
        ftu_cell_types_validated: _description_
    """

    pprint(ftu_cell_types)
    print()

    # collect PURLs for ASCT+B tables (alt: use https://lod.humanatlas.io/asct-b)
    hra_do_list = requests.get(
        "https://apps.humanatlas.io/api/kg/digital-objects", headers=accept_json
    ).json()

    # Compile list of nique organs covered by FTUs
    unique_organs = list({entry["organ_id"].split('/')[-1].replace('_',':') for entry in ftu_cell_types})
    print('Unique organs:')
    pprint(unique_organs)
    print()

    # Get PURLs for organs with FTUs
    purls = set()
    for do in hra_do_list['@graph']:
        if do['doType'] == 'asct-b':

            if 'organIds' in do:
                last_token = [
                    id.split("/")[-1].replace("_", ":") for id in do["organIds"]
                ]

                if any(token in unique_organs for token in last_token):
                    purl = do['@id'].replace('lod', 'purl')
                    purls.add(purl)

    print('PURLs:')
    pprint(purls)
    print()
    # for table in hra_do_list['@graph']:
    #     last_token = table['@id'].split('/')[-1]
    #

    # use https://apps.humanatlas.io/api/kg/digital-objects

    # For each FTU, get the ASCT+B table for the organ

    # for each FTU loop through cell types in the FTU illustration and check

    # Initialize result
    ftu_cell_types_validated = ftu_cell_types

    return ftu_cell_types_validated


def main():
    # Driver code

    # Get listing of FTUs and metadata (IRIS etc.) per organ
    organ_ftus = get_organs_with_ftus()

    # Use this listing of FTUs per organ to query the HRA KG for the cerll types in the FTU illustrations
    cell_types_per_ftu = compile_cell_types_per_ftu(organ_ftus)

    # Compare the cell types in the FTUs against ASCT+B tables and capture which appear only in the FTUs
    cell_types_per_ftu_validated = validate_against_asctb(cell_types_per_ftu)

if __name__ == "__main__":
    main()
