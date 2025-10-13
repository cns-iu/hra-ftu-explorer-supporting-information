# -*- coding: utf-8 -*-
"""
Robustly scan Input #1 for CellTypes whose `ccf_located_in` includes
UBERON:0002299 or UBERON:8410043. Works even if:
- cell types are nested deep,
- located_in values are strings (comma/space separated),
- IDs are OBO-style URIs (e.g., .../UBERON_8410043).
"""

from pathlib import Path
import json
import re
from typing import Any, Dict, List, Iterable, Set

# -------- EDIT THESE --------
INPUT1 = Path("enclosure-trees\data\lung_as.json")
OUTFILE = Path("cts_in_lung_ftus.json")
FTU_IDS = {"UBERON:0002299", "UBERON:8410043"}
# ----------------------------

ID_CURIE_RE = re.compile(r".*/([A-Za-z]+)_(\d+)$")  # .../UBERON_8410043 -> (UBERON,8410043)

def normalize_id(x: str) -> str:
    """
    Normalize IDs to CURIE form, e.g. UBERON:8410043.
    Accepts already-CURIE strings, trims, uppercases prefix.
    Converts OBO PURLs ending with PREFIX_NUMBER.
    """
    if not x or not isinstance(x, str):
        return x
    s = x.strip()
    m = ID_CURIE_RE.match(s)
    if m:
        return f"{m.group(1).upper()}:{m.group(2)}"
    # already looks like CURIE?
    if ":" in s and s.split(":", 1)[0].isalpha():
        pfx, rest = s.split(":", 1)
        return f"{pfx.upper()}:{rest}"
    return s

def normalize_id_list(val: Any) -> List[str]:
    """
    Turn ccf_located_in into a list of normalized CURIEs.
    Accepts list or string (comma/space separated).
    """
    if val is None:
        return []
    if isinstance(val, list):
        return [normalize_id(v) for v in val if isinstance(v, (str,))]
    if isinstance(val, str):
        # split on commas or whitespace
        parts = re.split(r"[,\s]+", val.strip())
        return [normalize_id(p) for p in parts if p]
    return []

def is_celltype(obj: Dict[str, Any]) -> bool:
    t1 = obj.get("conforms_to")
    t2 = obj.get("ccf_asctb_type")
    return (t1 == "CellType") or (t2 in {"CT", "CellType"})

def find_celltypes(root: Any) -> Iterable[Dict[str, Any]]:
    """
    Recursively yield dicts that look like CellType records.
    """
    if isinstance(root, dict):
        if is_celltype(root) or ("id" in root and ("ccf_located_in" in root or "ccf_pref_label" in root) and root.get("id","").startswith("CL:")):
            yield root
        for v in root.values():
            yield from find_celltypes(v)
    elif isinstance(root, list):
        for item in root:
            yield from find_celltypes(item)

def main():
    if not INPUT1.exists():
        print(f"ERROR: {INPUT1} not found"); return

    data = json.loads(INPUT1.read_text(encoding="utf-8"))

    # Normalize FTU IDs too (in case you change them later)
    ftu_norm: Set[str] = {normalize_id(x) for x in FTU_IDS}

    all_cts = list(find_celltypes(data))
    print(f"Scanned CellType-like records: {len(all_cts)}")

    matched = []
    hit_count = 0
    for ct in all_cts:
        cid = ct.get("id")
        label = ct.get("ccf_pref_label") or cid
        locs_raw = ct.get("ccf_located_in")
        locs = normalize_id_list(locs_raw)

        if any(loc in ftu_norm for loc in locs):
            matched.append({
                "id": cid,
                "label": label,
                "ccf_located_in": locs,  # normalized
            })
            hit_count += 1

    # Deduplicate by id (just in case the CT appeared in multiple places)
    dedup = {}
    for rec in matched:
        dedup[rec["id"]] = rec
    result = sorted(dedup.values(), key=lambda r: r["id"])

    OUTFILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Matched CTs: {len(result)}")
    print(f"Wrote -> {OUTFILE}")

    # Quick sanity preview
    for ex in result[:5]:
        print(" -", ex["id"], "|", ex["label"])

if __name__ == "__main__":
    main()
