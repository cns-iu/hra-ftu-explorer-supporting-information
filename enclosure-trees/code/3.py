"""
From Input #1 (AS+CT JSON), report for known FTU IDs:
  - immediate parents (ccf_part_of)
  - all ancestors up to the ORGAN_ID (inclusive)
  - all lineage paths from FTU up to ORGAN_ID (inclusive)

DAG-safe, handles CURIEs and OBO URIs.
"""

from pathlib import Path
import json, re
from typing import Any, Dict, List, Set

# -------- EDIT THESE --------
INPUT1   = Path("enclosure-trees\data\lung_as.json")  # your AS/CT catalog
FTU_IDS  = {"UBERON:0002299", "UBERON:8410043"}
ORGAN_ID = "UBERON:0002048"           # lung
OUTFILE  = Path("lung_ftu_lineage_to_organ.json")
# ----------------------------

ID_CURIE_RE = re.compile(r".*/([A-Za-z]+)_(\d+)$")
LABEL_KEYS = ("ccf_pref_label", "rdfs_label", "label", "name")

def normalize_id(x: Any) -> str:
    if not isinstance(x, str): return ""
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

def build_as_index(root: Any) -> Dict[str, Dict[str, Any]]:
    """
    Index AS-like records:
      as_index[id] = { label, part_of: [ids] }
    Treat as AS if tagged 'AS' or has ccf_part_of.
    """
    as_index: Dict[str, Dict[str, Any]] = {}
    def visit(node: Any):
        if isinstance(node, dict):
            rid  = normalize_id(node.get("id"))
            part = node.get("ccf_part_of")
            is_as = (node.get("ccf_asctb_type") == "AS") or isinstance(part, list)
            if rid and is_as:
                lbl = None
                for k in LABEL_KEYS:
                    v = node.get(k)
                    if isinstance(v, str) and v.strip():
                        lbl = v.strip(); break
                as_index[rid] = {
                    "label": lbl or rid,
                    "part_of": [normalize_id(x) for x in (part or []) if isinstance(x, str)]
                }
            for v in node.values(): visit(v)
        elif isinstance(node, list):
            for item in node: visit(item)
    visit(root)
    return as_index

def immediate_parents(as_index: Dict[str, Dict[str, Any]], node_id: str) -> List[str]:
    return list(as_index.get(node_id, {}).get("part_of", []))

def ancestors_to_organ(as_index: Dict[str, Dict[str, Any]], start_id: str, organ_id: str) -> Set[str]:
    """
    Transitive closure upward via ccf_part_of, but STOP when reaching organ_id.
    Includes organ_id if reachable.
    """
    organ_id = normalize_id(organ_id)
    seen: Set[str] = set()
    stack: List[str] = immediate_parents(as_index, start_id)
    while stack:
        cur = stack.pop()
        if cur in seen: 
            continue
        seen.add(cur)
        if cur == organ_id:
            # reached organ; do not traverse beyond
            continue
        stack.extend(immediate_parents(as_index, cur))
    # If start == organ, ensure organ present (though FTU won't be organ)
    return seen

def lineage_paths_to_organ(as_index: Dict[str, Dict[str, Any]], start_id: str, organ_id: str) -> List[List[str]]:
    """
    All paths from start_id up to ORGAN_ID (inclusive).
    If organ_id is not reachable, returns empty list.
    Cycle-safe.
    """
    organ_id = normalize_id(organ_id)
    paths: List[List[str]] = []
    visiting: Set[str] = set()

    def dfs(nid: str, path: List[str]):
        if nid in visiting:
            return
        visiting.add(nid)
        if nid == organ_id:
            paths.append(path + [nid])
            visiting.remove(nid)
            return
        parents = immediate_parents(as_index, nid)
        if not parents:
            # Dead-end without reaching organ: ignore this path
            visiting.remove(nid)
            return
        for p in parents:
            dfs(p, path + [nid])
        visiting.remove(nid)

    dfs(start_id, [])
    # ensure FTU->...->ORGAN order for each path
    return paths

def labelize(as_index: Dict[str, Dict[str, Any]], ids: List[str]) -> List[Dict[str, str]]:
    return [{"as_id": i, "as_label": as_index.get(i, {}).get("label", i)} for i in ids]

def main():
    data = load_json(INPUT1)
    as_index = build_as_index(data)
    organ_norm = normalize_id(ORGAN_ID)

    results = []
    for ftu in sorted(FTU_IDS):
        ftu_id = normalize_id(ftu)
        ftu_label = as_index.get(ftu_id, {}).get("label", ftu_id)

        # immediate parents
        parents_ids = immediate_parents(as_index, ftu_id)
        parents_named = labelize(as_index, parents_ids)

        # ancestors up to organ (set)
        anc_ids = ancestors_to_organ(as_index, ftu_id, organ_norm)
        # keep only those at or below organ (and include organ if reachable)
        if organ_norm in anc_ids or organ_norm in parents_ids:
            pass  # already included naturally if reachable
        # present sorted for stability but keep organ last if desired
        ancestors_named = labelize(as_index, sorted(anc_ids))

        # lineage paths up to organ (inclusive)
        paths_raw = lineage_paths_to_organ(as_index, ftu_id, organ_norm)
        paths_named = [labelize(as_index, p) for p in paths_raw]

        results.append({
            "ftu_id": ftu_id,
            "ftu_label": ftu_label,
            "parents": parents_named,
            "ancestors_to_organ": ancestors_named,
            "lineage_paths_to_organ": paths_named
        })

    OUTFILE.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"Wrote {OUTFILE}")
    for r in results:
        print(f"\nFTU {r['ftu_id']} | {r['ftu_label']}")
        if r["lineage_paths_to_organ"]:
            print(f"  paths to {ORGAN_ID}: {len(r['lineage_paths_to_organ'])}")
            # quick peek first path
            preview = "  " + " -> ".join([n['as_label'] for n in r["lineage_paths_to_organ"][0]])
            print(preview)
        else:
            print(f"  (no path to organ {ORGAN_ID} found)")

if __name__ == "__main__":
    main()
