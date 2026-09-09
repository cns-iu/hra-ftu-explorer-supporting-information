from shared import *
import pandas as pd

def main():
    cell_types_in_ftus = load_json(PIPELINE_OUTPUT_DIR / "cell-types-in-ftus.json")

    # TODO: replace with an actual count
    df = pd.DataFrame({"ftu_label": list(cell_types_in_ftus.keys())})
    save_df(df, "count_example.csv")


if __name__ == "__main__":
    main()
