# -*- coding: utf-8 -*-
"""
Build a hierarchy: Organ -> ... AS ... -> FTU -> CellTypes
for all paths from ORGAN to each FTU in FTU_IDS, using Input #1 (AS+CT catalog).

Outputs a single JSON tree with merged ancestors:
{
  "id": "UBERON:0002048", "label": "lung", "type": "AS",
  "children": [
    { "id": "...", "label": "...", "type": "AS", "children": [
        ...
        { "id": "UBERON:0002299", "label": "...", "type": "FTU", "children": [
            { "id": "CL:0002062", "label": "alveolar type I cell", "type": "CellType" },
            ...
        ]}
    ]}
  ]
}
"""

from pathlib import Path
import json, re
from typing import Any, Dict, List, Set

# ---------- EDIT THESE ----------
INPUT1    = Path("enclosure-trees\data\lung_as.json")          # AS+CT catalog
ORGAN_ID  = "UBERON:0002048"                   # lung
ORGAN_LABEL = "lung"                           # optional pretty label (used if not in data)
FTU_IDS   = {"UBERON:0002299", "UBERON:8410043"}
OUTFILE   = Path("hierarchy_organ_to_ct.json")
# ---------------------------------

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
    Index Anatomical Structures (and FTUs if present as AS):
      as_index[id] = { label, part_of: [ids] }
    Treat as AS if tagged ccf_asctb_type=='AS' OR has ccf_part_of.
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
            for it in node: visit(it)
    visit(root)
    return as_index

def collect_cell_types(root: Any) -> List[Dict[str, Any]]:
    """
    Gather CellType records with id, label, and ccf_located_in (list of normalized ids).
    Accepts either top-level 'cell_types' or nested.
    """
    out: List[Dict[str, Any]] = []
    def visit(node: Any):
        if isinstance(node, dict):
            is_ct = (node.get("conforms_to") == "CellType") or (node.get("ccf_asctb_type") in {"CT","CellType"})
            if is_ct and node.get("id", "").startswith("CL:"):
                cid = node["id"]
                label = node.get("ccf_pref_label") or node.get("label") or cid
                locs = node.get("ccf_located_in", [])
                if isinstance(locs, list):
                    locs_norm = [normalize_id(x) for x in locs if isinstance(x, str)]
                elif isinstance(locs, str):
                    import re
                    locs_norm = [normalize_id(x) for x in re.split(r"[,\s]+", locs.strip()) if x]
                else:
                    locs_norm = []
                out.append({"id": cid, "label": label, "located_in": locs_norm})
            for v in node.values(): visit(v)
        elif isinstance(node, list):
            for it in node: visit(it)
    visit(root)
    return out

def immediate_parents(as_index: Dict[str, Dict[str, Any]], node_id: str) -> List[str]:
    return list(as_index.get(node_id, {}).get("part_of", []))

def all_paths_to_organ(as_index: Dict[str, Dict[str, Any]], start_id: str, organ_id: str) -> List[List[str]]:
    """
    Return all paths [start, ..., organ] following 'part_of' upwards.
    If organ not reachable, return [].
    """
    organ_id = normalize_id(organ_id)
    paths: List[List[str]] = []
    visiting: Set[str] = set()

    def dfs(nid: str, path: List[str]):
        if nid in visiting:
            return  # cycle guard
        visiting.add(nid)
        if nid == organ_id:
            paths.append(path + [nid])
            visiting.remove(nid)
            return
        parents = immediate_parents(as_index, nid)
        if not parents:
            visiting.remove(nid)
            return
        for p in parents:
            dfs(p, path + [nid])
        visiting.remove(nid)

    dfs(start_id, [])
    return paths  # each from FTU -> ... -> ORGAN

def ensure_child(node: Dict[str, Any], child_id: str, child_label: str, child_type: str) -> Dict[str, Any]:
    """
    In 'node.children', find or create a child with id==child_id and return it.
    """
    if "children" not in node: node["children"] = []
    for ch in node["children"]:
        if ch.get("id") == child_id:
            return ch
    new_ch = {"id": child_id, "label": child_label, "type": child_type}
    node["children"].append(new_ch)
    return new_ch

def main():
    data = load_json(INPUT1)
    as_index = build_as_index(data)
    cts      = collect_cell_types(data)

    organ_id = normalize_id(ORGAN_ID)
    organ_label = as_index.get(organ_id, {}).get("label", ORGAN_LABEL or organ_id)

    # Map FTU -> CTs that explicitly locate_in that FTU
    ftu_to_cts: Dict[str, List[Dict[str, str]]] = {}
    for ct in cts:
        for loc in ct.get("located_in", []):
            if loc in FTU_IDS:
                ftu_to_cts.setdefault(loc, []).append({"id": ct["id"], "label": ct["label"]})

    # De-dup CTs per FTU
    for ftu, arr in ftu_to_cts.items():
        seen = {}
        for ct in arr:
            seen[ct["id"]] = ct
        ftu_to_cts[ftu] = sorted(seen.values(), key=lambda r: r["id"])

    # Build the hierarchy tree root
    root = {"id": organ_id, "label": organ_label, "type": "AS", "children": []}

    # For each FTU, compute all paths FTU->...->ORGAN, then add reversed to the tree
    for ftu in sorted(FTU_IDS):
        ftu_id = normalize_id(ftu)
        # Skip if FTU isn't known in AS index (still try to attach under organ directly)
        ftu_label = as_index.get(ftu_id, {}).get("label", ftu_id)

        paths = all_paths_to_organ(as_index, ftu_id, organ_id)
        if not paths:
            # Fall back: Organ -> FTU only
            branch = ensure_child(root, ftu_id, ftu_label, "FTU")
            # attach CTs
            for ct in ftu_to_cts.get(ftu_id, []):
                ensure_child(branch, ct["id"], ct["label"], "CellType")
            continue

        for path in paths:
            # path: [FTU, ..., ORGAN]; we need Organ->...->FTU
            rev = list(reversed(path))  # [ORGAN, ..., FTU]
            # walk/insert along the tree
            cur = root
            for idx, as_id in enumerate(rev):
                label = as_index.get(as_id, {}).get("label", as_id)
                typ = "AS"
                if idx == len(rev) - 1:  # last = FTU
                    typ = "FTU"
                if cur.get("id") == as_id:
                    # current node already matches (root == organ)
                    pass
                else:
                    cur = ensure_child(cur, as_id, label, typ)
            # at FTU node now; add CT leaves
            for ct in ftu_to_cts.get(ftu_id, []):
                ensure_child(cur, ct["id"], ct["label"], "CellType")

    OUTFILE.write_text(json.dumps(root, ensure_ascii=False, indent=2))
    print(f"Wrote {OUTFILE}")

if __name__ == "__main__":
    main()
