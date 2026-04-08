import json

target_source = (
    "https://entity.api.hubmapconsortium.org/entities/d482512016a61ef479960e2cb58552f2"
)
output_data = []

with open("../../raw-data/cell_type_populations_intermediary.jsonl", "r") as f:
    for i, line in enumerate(f):
        if not line.strip():
            continue

        data = json.loads(line)

        # Always save the first line
        if i == 0:
            output_data.append(data)

        # Save the target line
        elif data["cell_source"] == target_source:
            output_data.append(data)
            break

with open("test.json", "w", encoding="utf-8") as out_f:
    json.dump(output_data, out_f, ensure_ascii=False, indent=4)
