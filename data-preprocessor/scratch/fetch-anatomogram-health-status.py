import sys
from pathlib import Path

# shared.py lives in ../scripts; add it to the import path so this one-off can reuse it
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from shared import *  # noqa: E402,F403

# Relative to this script, so it works no matter which folder you run it from
INPUT_FOLDER = (
    Path(__file__).parent / config["ANATOMOGRAM_HEALTH_STATUS_JSON_FOLDER"]
)  # these were downloaded with bash
OUTPUT_FILE_NAME = ANATOMOGRAM_DATA_DIR / config["ANATOMOGRAM_HEALTH_STATUS_OUTPUT"]


def collect_json_files(folder: Path) -> list[Path]:
    # Every .json file in every subfolder of folder, e.g. json-files/ANATOMOGRAM-E-CURD-119-Healthy1/dataset.json
    return sorted(folder.glob("*/*.json"))


def make_look_up_id_health(json: dict) -> dict:
    # The keys we want to preserve, in this order (a tuple, not a set, so reruns write identical files)
    keys_to_keep = ("dataset_id", "donor_disease")

    # Create a new dict with only those keys
    filtered_dict = {k: json[k] for k in keys_to_keep if k in json}

    return filtered_dict


def save_to_json(json_list: list):
    with open(OUTPUT_FILE_NAME, "w", encoding="utf-8") as json_file_output:
        # indent=4 makes the JSON pretty-printed and easy to read
        json.dump(json_list, json_file_output, indent=4)


def count_healthy_vs_diseased(json_list: list):
    counter = 0
    for json_dict in json_list:
        if json_dict["donor_disease"].lower() != "healthy":
            counter = counter + 1
    print(f"Total disease: {counter}")


def main():
    print(f"JSON files are in {INPUT_FOLDER}.")
    print(f"Output goes into {OUTPUT_FILE_NAME}.")

    json_files = collect_json_files(INPUT_FOLDER)
    print(f"Found {len(json_files)} JSON files")

    json_list = []

    for json_file in json_files:
        # dataset_json = json.load(json_file)
        with open(json_file, "r") as f_json:
            json_data = json.load(f_json)
            json_list.append(make_look_up_id_health(json_data))

        # print(json_file)

    save_to_json(json_list)
    pprint(f"Saved: {json_list}")

    count_healthy_vs_diseased(json_list)


if __name__ == "__main__":
    main()
