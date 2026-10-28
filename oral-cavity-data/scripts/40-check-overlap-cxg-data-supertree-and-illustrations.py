from shared import *


def get_unique_cl_ids(cell_types: list):
    unique_cl_ids = set(cell_type["cl_id"] for cell_type in cell_types)
    return list(unique_cl_ids)


def check_if_supertree_or_illustration(cell_id: str, supertree, crosswalk):
    return {
        cell_id: {
            "is_in_supertree": check_if_cell_id_in_df(cell_id, df_supertree),
            "is_in_illustration": check_if_cell_id_in_df(cell_id, df_illustration),
        }
    }


def main():

    with open(CXG_DATA_JSON, "r") as f:
        data_json = json.load(f)
        # pprint(data_json)

        for dataset in data_json:
            print("===========")
            print(f"Unique CL IDs in {dataset}")
            # print(data_json[dataset])
            unique_cl_ids = get_unique_cl_ids(data_json[dataset])
            print(unique_cl_ids)
            print()

            for cl_id in unique_cl_ids:
                dict_is_in_both = check_if_supertree_or_illustration(
                    cl_id, df_supertree, df_illustration
                )

                for cell_type_dict in data_json[dataset]:
                    if cell_type_dict["cl_id"] == cl_id:
                        cell_type_dict.update(dict_is_in_both[cl_id])

    pprint(data_json)
    save_to_json(data_json)


if __name__ == "__main__":
    main()
