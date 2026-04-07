import json

with open("../../raw-data/cell_type_populations_intermediary.jsonl", "r") as f:
    first_line = f.readline()
    if first_line:
        data = json.loads(first_line)
        with open("test.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
