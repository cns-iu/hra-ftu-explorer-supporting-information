"""UpSet plot of the overlap in unique CL IDs across every file downloaded by 10-download-files.py.

Writes to reports/:
- upset-cl-id-overlap.png: the UpSet plot
- cl-id-overlap-intersections.csv: one row per intersection (which files, how many CL IDs)
- cl-id-overlap-memberships.csv: one row per CL ID, with a True/False column per file
"""

import json
import warnings

import matplotlib

matplotlib.use("Agg")  # write files only, no window
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd
from upsetplot import UpSet, from_contents

from shared import DOWNLOADS, REPORTS_DIR, download_path

plt.rcParams["font.family"] = "Arial"

# The 2D FTU crosswalk CSV has 11 metadata lines (title, authors, DOI, ...) before the header row
FTU_CROSSWALK_METADATA_ROWS = 11


def cl_ids_from_ftu_crosswalk_csv(path) -> set[str]:
    """CL IDs of the cell types in the 2D FTU illustrations (OntologyID also holds UBERON IDs for AS nodes, dropped here)."""
    df = pd.read_csv(path, skiprows=FTU_CROSSWALK_METADATA_ROWS)
    ids = df["OntologyID"].dropna().astype(str).str.strip()
    return set(ids[ids.str.startswith("CL:")])


def cl_ids_from_ctann_json(path) -> set[str]:
    """CL IDs that an annotation tool's labels are mapped to (any predicate: exact, narrow or broad match)."""
    with open(path, "r", encoding="utf-8") as f:
        mappings = json.load(f)["data"]["mappings"]
    ids = (str(m.get("object_id", "")).strip() for m in mappings)
    return {i for i in ids if i.startswith("CL:")}


READERS = {
    "ftu-crosswalk-csv": cl_ids_from_ftu_crosswalk_csv,
    "ctann-json": cl_ids_from_ctann_json,
}

cl_ids_per_file = {
    entry["label"]: READERS[entry["format"]](download_path(key))
    for key, entry in DOWNLOADS.items()
}
for label, ids in cl_ids_per_file.items():
    print(f"{label}: {len(ids)} unique CL IDs")
all_ids = set().union(*cl_ids_per_file.values())
print(f"All files combined: {len(all_ids)} unique CL IDs")

# One row per CL ID with a True/False column per file
memberships = pd.DataFrame(
    {
        label: [cl_id in ids for cl_id in sorted(all_ids)]
        for label, ids in cl_ids_per_file.items()
    },
    index=pd.Index(sorted(all_ids), name="cl_id"),
)
memberships.to_csv(REPORTS_DIR / "cl-id-overlap-memberships.csv")

intersections = (
    memberships.value_counts()
    .rename("cl_id_count")
    .reset_index()
    .sort_values("cl_id_count", ascending=False)
)
intersections.insert(
    0,
    "files",
    intersections[list(cl_ids_per_file)].apply(
        lambda row: " & ".join(row.index[row]), axis=1
    ),
)
intersections.to_csv(REPORTS_DIR / "cl-id-overlap-intersections.csv", index=False)

# UpSetPlot 0.9.0 triggers pandas chained-assignment FutureWarnings internally; harmless with pandas<3
warnings.filterwarnings("ignore", category=FutureWarning, module="upsetplot")

# UpSetPlot's own show_counts crashes with numpy 2 / matplotlib 3.10, so label the bars ourselves
fig = plt.figure(figsize=(14, 7))
upset = UpSet(
    from_contents(cl_ids_per_file),
    subset_size="count",
    sort_by="cardinality",
    show_counts=False,
)
axes = upset.plot(fig=fig)
axes["intersections"].bar_label(axes["intersections"].containers[0])
axes["totals"].bar_label(axes["totals"].containers[0], padding=2)
# Default figure title size is "large" (12 pt at the default 10 pt base size); double it
default_title_pt = FontProperties(size=plt.rcParams["figure.titlesize"]).get_size_in_points()
fig.suptitle(f"Overlap in unique CL IDs ({len(all_ids)} in total)", fontsize=2 * default_title_pt)
out_png = REPORTS_DIR / "upset-cl-id-overlap.png"
fig.savefig(out_png, dpi=600, bbox_inches="tight")
plt.close(fig)
print(
    f"Saved {out_png.name}, cl-id-overlap-intersections.csv, cl-id-overlap-memberships.csv to {REPORTS_DIR}"
)
