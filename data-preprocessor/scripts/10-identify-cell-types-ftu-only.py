from shared import *


def get_organ():

    url = "https://apps.humanatlas.io/api/grlc/hra/2d-ftu-parts.csv"

    headers = {"Accept": "text/csv"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    ftu_parts = pd.read_csv(StringIO(response.text))

    # print(ftu_parts.head())

    ftu_organ_lookup = ftu_parts[
        ["ftu_digital_object", "organ_id", "organ_label"]
    ].drop_duplicates()

    print(ftu_organ_lookup)

    return ftu_organ_lookup


def compile_cell_types_per_ftu(query_result: pd.DataFrame, organ_lookup: pd.DataFrame):

    result = {}

    for row in query_result.itertuples(index=False):
        ftu_purl = row.ftu_purl
        ftu_label = row.ftu_label
        ct_label = row.ct_label
        ct_iri = iri_to_curie(row.ct_iri)

        # Initialize entry if not exists
        if ftu_label not in result:
            # print(type(organ_lookup))
            # print(organ_lookup)

            # organ_data = (
            #     organ_lookup[["ftu_iri", "organ_id", "organ_label"]]
            #     .drop_duplicates()
            #     .set_index("ftu_iri")[["organ_id", "organ_label"]]
            #     .to_dict(orient="index")
            # )

            # organ_info = organ_data.get("ftu_iri", {})

            # organ_id = organ_info.get('organ_id')
            # organ_label = organ_info.get('organ_label')
            print(ftu_purl)
            matches = organ_lookup.loc[
                organ_lookup["ftu_digital_object"] == ftu_purl,
                ["organ_id", "organ_label"],
            ]

            found = tuple(matches.itertuples(index=False, name=None))
            print(found)

            if found:
                organ_id_short, organ_label = found[0]
            else:
                organ_id_short, organ_label = None, None

            result[ftu_label] = {
                "ftu_purl": ftu_purl,
                "cts_in_2d_ftu": [],
                "cts_in_asctb": [],
                "cts_exclusive": [],
                "organ_id_short": organ_id_short,
                "organ_label": organ_label,
            }

        # Append based on flags
        if as_bool(getattr(row, "in_2d_ftu", True)):
            result[ftu_label]["cts_in_2d_ftu"].append(
                {"ct_label": ct_label, "ct_iri": ct_iri}
            )

        if as_bool(getattr(row, "in_asctb", True)):
            result[ftu_label]["cts_in_asctb"].append(
                {"ct_label": ct_label, "ct_iri": ct_iri}
            )

        if as_bool(getattr(row, "exclusive_ct_in_ftu", True)):
            result[ftu_label]["cts_exclusive"].append(
                {"ct_label": ct_label, "ct_iri": ct_iri}
            )

    # pprint(result)

    with open(CELL_TYPES_IN_FTUS, "w") as f:
        json.dump(result, f, indent=2)

    print(f"✅ Saved data to {CELL_TYPES_IN_FTUS}")

    return result


def main():
    # Driver code

    ftu_query = pd.read_csv(FTU_QUERY)

    result = compile_cell_types_per_ftu(ftu_query, get_organ())

    for item in result:
        pprint(item + " " + str(len(result[item]["cts_exclusive"])))


if __name__ == "__main__":
    main()
