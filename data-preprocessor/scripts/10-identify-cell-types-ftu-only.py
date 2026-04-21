from shared import *


def compile_cell_types_per_ftu(query_result: pd.DataFrame):

    result = {}

    for row in query_result.itertuples(index=False):
        ftu_purl = row.ftu_purl
        ftu_label = row.ftu_label
        ct_label = row.ct_label
        ct_iri = iri_to_curie(row.ct_iri)
        organ_id_short = iri_to_curie(row.organ_iri)
        organ_label = row.organ_label

        # Initialize entry if not exists
        if ftu_label not in result:
            print(ftu_purl)

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

    result = compile_cell_types_per_ftu(ftu_query)

    for item in result:
        pprint(item + " " + str(len(result[item]["cts_exclusive"])))


if __name__ == "__main__":
    main()
