from shared import *

# Each supertree row is one path from the root (cell, CL:0000000) down to a leaf; ancestors are to the left
SUPERTREE_ID_COLUMNS = [c for c in df_supertree.columns if c.endswith("/ID")]
# Only CL IDs in the mouth (oral cavity) illustration count, not those of other organs' illustrations
ILLUSTRATION_IDS = set(df_illustrations_mouth["OntologyID"])


def get_parent_class_in_illustration(cell_id: str):
    """Walk left from cell_id in a supertree row and return the first (closest) ancestor CL ID in the mouth illustration, else None.

    Every CL ID has exactly one ancestor path in the supertree, so the first row containing it is enough.
    """
    for row in df_supertree[SUPERTREE_ID_COLUMNS].itertuples(index=False):
        row = list(row)
        if cell_id in row:
            for ancestor_id in reversed(row[: row.index(cell_id)]):
                if ancestor_id in ILLUSTRATION_IDS:
                    return ancestor_id
            return None
    return None


def main():
    with open(CXG_DATA_JSON, "r") as f:
        data_json = json.load(f)

    for dataset in data_json:
        for cell_type_dict in data_json[dataset]:
            if (
                cell_type_dict["is_in_supertree"]
                and not cell_type_dict["is_in_illustration"]
            ):
                cell_type_dict["ancestor_class_in_supertree"] = (
                    get_parent_class_in_illustration(cell_type_dict["cl_id"])
                )

    pprint(data_json)
    save_to_json(data_json)


if __name__ == "__main__":
    main()
