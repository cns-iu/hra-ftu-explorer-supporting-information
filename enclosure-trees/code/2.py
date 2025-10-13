# -*- coding: utf-8 -*-
"""
Enrich CT records by mapping ccf_located_in IDs to AS names using a robust
id->label index built by recursively scanning Input #1.
"""

from pathlib import Path
import json, re
from typing import Any, Dict, List, Set

# ---------- EDIT THESE ----------
INPUT1_AS_CT = Path("enclosure-trees\data\lung_as.json")         # full AS+CT catalog
INPUT_CT_LIST = Path("cts_in_lung_ftus.json")    # CTs you filtered earlier
OUTPUT_ENRICHED = Path("cts_in_lung_ftus_as.json")
# Optional manual overrides if some labels are missing in Input #1:
MANUAL_LABELS = {
    # "UBERON:8410043": "bronchial submucosal gland",
    # "UBERON:0002299": "lung alveolus (example)",
}
# --------------------------------

# .../UBERON_8410043  → UBERON:8410043
ID_CURIE_RE = re.compile(r".*/([A-Za-z]+)_(\d+)$")

LABEL_KEYS = ("ccf_pref_label", "rdfs_label", "label", "name")

def normalize_id(x: Any) -> str:
    if not isinstance(x, str):
        return ""
    s = x.strip()
    m = ID_CURIE_RE.match(s)
    if m:
        return f"{m.group(1).upper()}:{m.group(2)}"
    if ":" in s and s.split(":", 1)[0].isalpha():
        pfx, rest = s.split(":", 1)
        return f"{pfx.upper()}:{rest}"
    return s

def load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))

def collect_id_label_pairs(root: Any, idx: Dict[str, str]) -> None:
    """Recursively collect id->label from ANY dict that has an id plus a label-like field."""
    if isinstance(root, dict):
        rid = normalize_id(root.get("id"))
        if rid:
            # Prefer the first present label key
            lbl = None
            for k in LABEL_KEYS:
                v = root.get(k)
                if isinstance(v, str) and v.strip():
                    lbl = v.strip()
                    break
            if lbl:
                # don't overwrite an existing nicer label
                if rid not in idx or len(lbl) > len(idx[rid]):
                    idx[rid] = lbl
        for v in root.values():
            collect_id_label_pairs(v, idx)
    elif isinstance(root, list):
        for item in root:
            collect_id_label_pairs(item, idx)

def normalize_loc_list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [normalize_id(x) for x in val if isinstance(x, str)]
    if isinstance(val, str):
        parts = re.split(r"[,\s]+", val.strip())
        return [normalize_id(p) for p in parts if p]
    return []

def main():
    as_ct_data = load_json(INPUT1_AS_CT)
    ct_list = load_json(INPUT_CT_LIST)

    # Build a comprehensive id->label map from the entire Input #1
    id2label: Dict[str, str] = {}
    collect_id_label_pairs(as_ct_data, id2label)

    # Apply manual overrides last
    id2label.update(MANUAL_LABELS)

    # Enrich CTs
    enriched = []
    missing_labels: Set[str] = set()
    for ct in ct_list:
        loc_ids = normalize_loc_list(ct.get("ccf_located_in", []))
        loc_named = []
        for lid in loc_ids:
            lbl = id2label.get(lid)
            if not lbl:
                missing_labels.add(lid)
                lbl = lid  # fallback to id
            loc_named.append({"as_id": lid, "as_label": lbl})

        out_ct = dict(ct)
        # Remove the original ccf_located_in field
        out_ct.pop("ccf_located_in", None)
        out_ct["ccf_located_in_named"] = loc_named
        enriched.append(out_ct)

    OUTPUT_ENRICHED.write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
    print(f"Enriched {len(enriched)} CTs  → {OUTPUT_ENRICHED}")
    if missing_labels:
        print("Note: missing labels for", len(missing_labels), "IDs.")
        # Uncomment to inspect:
        # for m in sorted(missing_labels): print("  -", m)

if __name__ == "__main__":
    main()