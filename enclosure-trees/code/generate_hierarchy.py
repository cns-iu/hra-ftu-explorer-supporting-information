# -*- coding: utf-8 -*-
"""
One-shot pipeline to produce a unified Organ → AS → FTU → CellType hierarchy
from an AS+CT JSON catalog.

Stages (in-memory by default, optional intermediate dumps):
  1) Filter CTs: keep only CTs whose ccf_located_in includes any FTU id
  2) Enrich CTs: map ccf_located_in IDs → AS labels (using an id→label index)
  3) Trace FTU lineage: all FTU→…→ORGAN paths via ccf_part_of
  4) Build final merged tree: Organ → … AS … → FTU → CT leaves

Usage (example for lung):
  python build_hierarchy.py \
    --input enclosure-trees/data/lung_as.json \
    --organ-id UBERON:0002048 \
    --organ-label "lung" \
    --ftu-ids UBERON:0002299,UBERON:8410043 \
    --output hierarchy_organ_to_ct.json

Optional:
  --save-intermediates        # writes stage outputs next to --output
  --manual-label UBERON:8410043="bronchial submucosal gland"
  --manual-label UBERON:0002299="alveolus of lung on respiratory bronchiole"
"""

from __future__ import annotations
from pathlib import Path
import argparse
import json
import re
from typing import Any, Dict, Iterable, List, Set, Tuple

# ------------------------
# Helpers: ID normalization
# ------------------------

ID_CURIE_RE = re.compile(r".*/([A-Za-z]+)_(\d+)$")  # .../UBERON_8410043 → (UBERON, 8410043)

def normalize_id(x: Any) -> str:
    """Normalize ID to CURIE form PREFIX:NUMBER, keep as-is if already CURIE-like."""
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

def normalize_id_list(val: Any) -> List[str]:
    """Turn ccf_located_in into list of normalized CURIE strings."""
    if val is None:
        return []
    if isinstance(val, list):
        return [normalize_id(v) for v in val if isinstance(v, str)]
    if isinstance(val, str):
        parts = re.split(r"[,\s]+", val.strip())
        return [normalize_id(p) for p in parts if p]
    return []

# ------------------------
# I/O
# ------------------------

def load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))

def dump_json(p: Path, obj: Any) -> None:
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

# ------------------------
# Stage 0: indices & scans
# ------------------------

LABEL_KEYS = ("ccf_pref_label", "rdfs_label", "label", "name")

def build_as_index(root: Any) -> Dict[str, Dict[str, Any]]:
    """
    Index AS-like records: as_index[id] = {label, part_of: [ids]}
    Treat node as AS if tagged ccf_asctb_type=='AS' OR has ccf_part_of (list).
    """
    as_index: Dict[str, Dict[str, Any]] = {}

    def visit(node: Any):
        if isinstance(node, dict):
            rid = normalize_id(node.get("id"))
            part = node.get("ccf_part_of")
            is_as = (node.get("ccf_asctb_type") == "AS") or isinstance(part, list)
            if rid and is_as:
                lbl = None
                for k in LABEL_KEYS:
                    v = node.get(k)
                    if isinstance(v, str) and v.strip():
                        lbl = v.strip()
                        break
                as_index[rid] = {
                    "label": lbl or rid,
                    "part_of": [normalize_id(x) for x in (part or []) if isinstance(x, str)],
                }
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for it in node:
                visit(it)

    visit(root)
    return as_index

def collect_cell_types(root: Any) -> List[Dict[str, Any]]:
    """
    Collect CellType dicts with fields: id, label, located_in(list of ids).
    Accepts nested presence; recognizes via conforms_to=='CellType' or ccf_asctb_type in {'CT','CellType'}.
    """
    out: List[Dict[str, Any]] = []

    def visit(node: Any):
        if isinstance(node, dict):
            is_ct = (node.get("conforms_to") == "CellType") or (node.get("ccf_asctb_type") in {"CT", "CellType"})
            nid = node.get("id", "")
            if is_ct and isinstance(nid, str) and nid.startswith("CL:"):
                label = node.get("ccf_pref_label") or node.get("label") or nid
                locs = normalize_id_list(node.get("ccf_located_in"))
                out.append({"id": nid, "label": label, "located_in": locs})
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for it in node:
                visit(it)

    visit(root)
    return out

def collect_id_label_pairs(root: Any) -> Dict[str, str]:
    """Recursively collect id->label for any dict having an id + any label-like key."""
    idx: Dict[str, str] = {}

    def visit(node: Any):
        if isinstance(node, dict):
            rid = normalize_id(node.get("id"))
            if rid:
                lbl = None
                for k in LABEL_KEYS:
                    v = node.get(k)
                    if isinstance(v, str) and v.strip():
                        lbl = v.strip()
                        break
                if lbl and (rid not in idx or len(lbl) > len(idx[rid])):
                    idx[rid] = lbl
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for it in node:
                visit(it)

    visit(root)
    return idx

# ------------------------
# Stage 1: filter CTs by FTU location
# ------------------------

def filter_cts_in_ftus(cts: List[Dict[str, Any]], ftu_ids: Set[str]) -> List[Dict[str, Any]]:
    ftu_ids_norm = {normalize_id(x) for x in ftu_ids}
    matched = []
    for ct in cts:
        locs = ct.get("located_in", [])
        if any(loc in ftu_ids_norm for loc in locs):
            matched.append({"id": ct["id"], "label": ct["label"], "ccf_located_in": locs})
    # dedup by id
    dedup = {rec["id"]: rec for rec in matched}
    return sorted(dedup.values(), key=lambda r: r["id"])

# ------------------------
# Stage 2: enrich CTs with AS labels for their locations
# ------------------------

def enrich_ct_locations_with_labels(ct_list: List[Dict[str, Any]], id2label: Dict[str, str]) -> Tuple[List[Dict[str, Any]], Set[str]]:
    enriched = []
    missing: Set[str] = set()
    for ct in ct_list:
        loc_ids = normalize_id_list(ct.get("ccf_located_in", []))
        loc_named = []
        for lid in loc_ids:
            lbl = id2label.get(lid) or lid
            if lid not in id2label:
                missing.add(lid)
            loc_named.append({"as_id": lid, "as_label": lbl})
        out_ct = dict(ct)
        out_ct.pop("ccf_located_in", None)
        out_ct["ccf_located_in_named"] = loc_named
        enriched.append(out_ct)
    return enriched, missing

# ------------------------
# Stage 3: lineage paths FTU → … → ORGAN via ccf_part_of
# ------------------------

def immediate_parents(as_index: Dict[str, Dict[str, Any]], node_id: str) -> List[str]:
    return list(as_index.get(node_id, {}).get("part_of", []))

def all_paths_to_organ(as_index: Dict[str, Dict[str, Any]], start_id: str, organ_id: str) -> List[List[str]]:
    """
    Return all paths [start, ..., organ] following 'part_of' upwards. Empty if organ unreachable.
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
            visiting.remove(nid)
            return
        for p in parents:
            dfs(p, path + [nid])
        visiting.remove(nid)

    dfs(start_id, [])
    return paths

# ------------------------
# Stage 4: build final merged tree
# ------------------------

def ensure_child(node: Dict[str, Any], child_id: str, child_label: str, child_type: str) -> Dict[str, Any]:
    if "children" not in node:
        node["children"] = []
    for ch in node["children"]:
        if ch.get("id") == child_id:
            return ch
    new_ch = {"id": child_id, "label": child_label, "type": child_type}
    node["children"].append(new_ch)
    return new_ch

def build_final_hierarchy(
    as_index: Dict[str, Dict[str, Any]],
    organ_id: str,
    organ_label: str,
    ftu_ids: Set[str],
    ftu_to_cts: Dict[str, List[Dict[str, str]]],
) -> Dict[str, Any]:
    root = {"id": organ_id, "label": organ_label, "type": "AS", "children": []}
    for ftu in sorted(ftu_ids):
        ftu_id = normalize_id(ftu)
        ftu_label = as_index.get(ftu_id, {}).get("label", ftu_id)
        paths = all_paths_to_organ(as_index, ftu_id, organ_id)

        if not paths:
            # Fallback: attach FTU directly under organ
            branch = ensure_child(root, ftu_id, ftu_label, "FTU")
            for ct in ftu_to_cts.get(ftu_id, []):
                ensure_child(branch, ct["id"], ct["label"], "CellType")
            continue

        for path in paths:
            # path is [FTU, ..., ORGAN]; reverse to Organ→…→FTU
            rev = list(reversed(path))
            cur = root
            for idx, as_id in enumerate(rev):
                label = as_index.get(as_id, {}).get("label", as_id)
                typ = "FTU" if idx == len(rev) - 1 else "AS"
                if cur.get("id") == as_id:
                    # already at this node (root == organ)
                    pass
                else:
                    cur = ensure_child(cur, as_id, label, typ)
            # at FTU node; add CT leaves
            for ct in ftu_to_cts.get(ftu_id, []):
                ensure_child(cur, ct["id"], ct["label"], "CellType")
    return root

# ------------------------
# CLI / Orchestration
# ------------------------
def slugify(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-') or 'organ'

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build Organ→AS→FTU→CT hierarchy from AS+CT JSON catalog.")
    ap.add_argument("--input", required=True, type=Path, help="AS+CT catalog JSON (e.g., lung_as.json)")
    ap.add_argument("--organ-id", required=True, help="Organ CURIE (e.g., UBERON:0002048)")
    ap.add_argument("--organ-label", default="", help="Optional organ label override (uses data if absent)")
    ap.add_argument("--ftu-ids", required=True, help="Comma-separated FTU IDs (CURIEs or OBO URIs)")
    ap.add_argument("--output", required=True, type=Path, help="Output JSON path for final hierarchy")
    ap.add_argument("--save-intermediates", action="store_true", help="Write intermediate JSONs next to output")
    ap.add_argument(
        "--manual-label",
        action="append",
        default=[],
        help='Manual AS label override(s), e.g. UBERON:8410043="bronchial submucosal gland"',
    )
    return ap.parse_args()

def parse_manual_labels(pairs: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for s in pairs:
        # Accept forms: KEY=VAL or KEY="VAL with spaces"
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = normalize_id(k.strip())
        v = v.strip().strip('"').strip("'")
        if k:
            out[k] = v
    return out

def main():
    args = parse_args()

    # Load data
    data = load_json(args.input)

    # Indices and scans
    as_index = build_as_index(data)
    id2label = collect_id_label_pairs(data)

    # Apply manual label overrides last
    id2label.update(parse_manual_labels(args.manual_label))
    for k, v in list(id2label.items()):
        # keep AS index label consistent if override targets existing AS
        if k in as_index:
            as_index[k]["label"] = v

    organ_id = normalize_id(args.organ_id)
    organ_label = args.organ_label or as_index.get(organ_id, {}).get("label", organ_id)

    args.output = args.output.parent / f"{slugify(organ_label or organ_id)}_{args.output.name}"

    # Gather cell types
    cts = collect_cell_types(data)

    # Stage 1: filter CTs by FTU
    ftu_ids: Set[str] = {normalize_id(s) for s in re.split(r"[,\s]+", args.ftu_ids) if s.strip()}
    cts_in_ftu = filter_cts_in_ftus(cts, ftu_ids)

    # Stage 2: enrich CTs with AS labels
    enriched_cts, missing_labels = enrich_ct_locations_with_labels(cts_in_ftu, id2label)

    # Map FTU→CTs (id+label) from enriched set
    ftu_to_cts: Dict[str, List[Dict[str, str]]] = {}
    for ct in enriched_cts:
        for loc in ct.get("ccf_located_in_named", []):
            as_id = loc["as_id"]
            if as_id in ftu_ids:
                ftu_to_cts.setdefault(as_id, []).append({"id": ct["id"], "label": ct["label"]})
    # de-dup per FTU
    for ftu, arr in ftu_to_cts.items():
        uniq = {c["id"]: c for c in arr}
        ftu_to_cts[ftu] = sorted(uniq.values(), key=lambda r: r["id"])

    # Stage 4: build final hierarchy (Stage 3 lineage is used internally here via all_paths_to_organ)
    final_tree = build_final_hierarchy(as_index, organ_id, organ_label, ftu_ids, ftu_to_cts)

    # Output(s)
    dump_json(args.output, final_tree)

    if args.save_intermediates:
        base = args.output.with_suffix("")
        dump_json(base.with_name(base.name + "_cts_in_ftus.json"), cts_in_ftu)
        dump_json(base.with_name(base.name + "_cts_in_ftus_as.json"), enriched_cts)

        # Optional: lineage preview for each FTU (IDs only)
        lineage_preview = {}
        for ftu in sorted(ftu_ids):
            lineage_preview[ftu] = all_paths_to_organ(as_index, ftu, organ_id)
        dump_json(base.with_name(base.name + "_ftu_lineage_to_organ.json"), lineage_preview)

    # Logs
    print(f"[OK] Final hierarchy → {args.output}")
    print(f"     Organ: {organ_id} | Label: {organ_label}")
    print(f"     FTUs: {', '.join(sorted(ftu_ids))}")
    print(f"     CTs located in FTUs: {len(cts_in_ftu)}")
    if missing_labels:
        print(f"     Note: missing AS labels for {len(missing_labels)} IDs (fallback to IDs).")

if __name__ == "__main__":
    main()
