from shared import *

# How hra-ui reads each data source (libs/services/src/lib/ftu-data/ftu-data.impl.ts, toSourceReferences):
#   "@id"       -> datasetId     (Dataset ID column; ALSO matched against cell_source in
#                                 ftu-cell-summaries.jsonld by filterSummaries, so it must stay
#                                 "<dataset_id>#CellSummary_<ftu suffix>", same as script 41)
#   label       -> datasetTitle  (Dataset Title column)
#   link        -> doi           (Publication DOI column)
#   description -> title         (Publication Title column)
#   year        -> year          (Publication Year column; -1 when missing)
# The remaining columns (cellType, healthStatus, sex, age, bmi, ethnicity) are not read from the
# file by hra-ui yet. We emit them below under snake_case keys so hra-ui only has to map them.

ANNOTATION_TOOL_LABELS = {
    "azimuth": "Azimuth",
    "celltypist": "CellTypist",
    "popv": "popV",
    # Only in the anatomogram data
    "pan-human-azimuth": "Pan-Human Azimuth",
    "author": "Author annotation",
    "frmatch": "FR-Match",
}

# Required (non-optional) strings in hra-ui's RAW_DATASETS schema
REQUIRED_STRING_FIELDS = {"label", "link", "description"}

MISSING_VALUES = {"", "unknown", "nan", "none", "not reported", "na"}


def clean(value):
    """Returns a stripped string, or None for NaN/empty/'unknown' values"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    value = str(value).strip()
    return None if value.lower() in MISSING_VALUES else value


def to_number(value):
    """Returns an int for whole numbers, a float otherwise, or None if not numeric"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(number):
        return None
    return int(number) if number.is_integer() else round(number, 2)


def get_age(row):
    """Donor age in years from donor_age, else parsed from a CxG '<N>-year-old stage' development stage"""
    age = to_number(row["donor_age"])
    if age is not None:
        return age
    match = re.fullmatch(r"(\d+)-year-old stage", str(row["donor_development_stage"]).strip())
    return int(match.group(1)) if match else None


def get_sex(value):
    value = clean(value)
    return value.capitalize() if value else None


def get_doi_metadata(dois):
    """Fetches title/year/authors for each DOI from Crossref, cached in raw-data/ between runs"""
    cache = {}
    if DOI_METADATA_CACHE.exists():
        with open(DOI_METADATA_CACHE, "r", encoding="utf-8") as f:
            cache = json.load(f)

    for doi in tqdm(sorted(set(dois) - set(cache)), desc="Fetching DOI metadata"):
        bare_doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
        try:
            response = requests.get(
                f"https://api.crossref.org/works/{bare_doi}", timeout=30
            )
            response.raise_for_status()
        except requests.RequestException as e:
            tqdm.write(f"{Fore.YELLOW}Could not fetch {doi}: {e}{Style.RESET_ALL}")
            continue

        message = response.json()["message"]
        date_parts = (message.get("issued") or {}).get("date-parts") or [[None]]
        cache[doi] = {
            "title": (message.get("title") or [None])[0],
            "year": date_parts[0][0],
            "authors": [
                " ".join(filter(None, [a.get("given"), a.get("family")]))
                for a in message.get("author", [])
                if a.get("family")
            ],
        }

    with open(DOI_METADATA_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

    return cache


def get_preferred_tool_and_cts_by_dataset():
    """dataset_id -> (the one annotation tool used for it, the cell types that tool found),
    matching what 41 puts into the cell summaries"""
    tool_and_cts = {}
    for obj in iterate_preferred_cell_summaries():
        _, cts = tool_and_cts.setdefault(obj["cell_source"], (obj["annotation_method"], set()))
        # Some HRApop rows have gene_expr == "[]" (a string, no genes); 41 skips those, so skip them here too
        cts.update(
            summary["cell_id"]
            for summary in obj.get("summary", [])
            if isinstance(summary.get("gene_expr"), list) and summary["gene_expr"]
        )
    return tool_and_cts


def get_dataset_title(row):
    """Human-readable dataset title: CxG collection title + donor, or the portal ID (HBM…, SNT…, GTEX-…)"""
    if row["handler"] == "cellxgene":
        donor = row["dataset_id"].rsplit("#", 1)[-1].split("$", 1)[0]
        return f"{clean(row['publication_title'])} (donor {donor})"
    return row["id"]


def build_data_source(row, dataset_id, ftu_suffix, annotation_tool, doi_metadata):
    doi = clean(row["publication"])
    paper = doi_metadata.get(doi, {}) if doi else {}

    authors = paper.get("authors") or [
        clean(row["publication_lead_author"]) or clean(row["provider_name"])
    ]

    data_source = {
        "@id": f"{dataset_id}#CellSummary_{ftu_suffix}",
        "@type": "Dataset",
        "label": get_dataset_title(row),
        "link": doi or "",
        "description": paper.get("title") or clean(row["publication_title"]) or "",
        "year": paper.get("year"),
        "authors": [a for a in authors if a],
        "dataset_id": dataset_id,
        "dataset_link": clean(row["dataset_link"]),
        "cell_type_annotation_tool": ANNOTATION_TOOL_LABELS.get(
            annotation_tool, annotation_tool
        ),
        # health_status: not in HRApop's dataset metadata, so not emitted yet
        "sex": get_sex(row["donor_sex"]),
        "age": get_age(row),
        "development_stage": clean(row["donor_development_stage"]),
        "bmi": to_number(row["donor_bmi"]),
        "ethnicity": clean(row["donor_race"]),
    }

    # hra-ui's zod schema has optional (not nullable) fields, so drop empty values,
    # except for the strings it requires
    return {
        k: v
        for k, v in data_source.items()
        if k in REQUIRED_STRING_FIELDS or v not in (None, "", [])
    }


def apply_doi_overrides(metadata: pd.DataFrame) -> pd.DataFrame:
    """Fills in `publication` from config's DOI_OVERRIDES (CellxGene collection ID -> DOI)
    for datasets that have none, so Crossref can supply their title/year/authors"""
    metadata = metadata.copy()
    collection_ids = metadata["dataset_id"].str.extract(
        r"/collections/([0-9a-f-]+)", expand=False
    )
    override_dois = collection_ids.map(config.get("DOI_OVERRIDES") or {})
    missing = metadata["publication"].map(clean).isna() & override_dois.notna()
    metadata.loc[missing, "publication"] = override_dois[missing]
    print(f"Filled in {missing.sum()} missing DOI(s) from DOI_OVERRIDES")
    return metadata


def build_ftu_datasets_jsonld(metadata: pd.DataFrame):
    out_json_ld = copy.deepcopy(context_template)

    tool_and_cts_by_dataset = get_preferred_tool_and_cts_by_dataset()

    exclusive_cts_by_ftu = load_exclusive_cts_by_ftu()

    # A dataset belongs to an FTU only if its preferred annotation tool found a CT that is
    # exclusive to that FTU in the current cell-types-in-ftus.json, i.e., exactly when 41
    # writes a cell summary for it (so the table has no rows without expression data)
    ftu_to_datasets = defaultdict(set)
    for dataset_id, matches in load_filtered_dataset_metadata().items():
        _, preferred_cts = tool_and_cts_by_dataset.get(dataset_id, (None, set()))
        for match in matches:
            ftu = match["ftu_purl"]
            ct = get_id_from_iri(match["ct_iri"])
            if ct in preferred_cts and ct in exclusive_cts_by_ftu.get(ftu, set()):
                ftu_to_datasets[ftu].add(dataset_id)
    ftu_to_datasets = {k: sorted(v) for k, v in ftu_to_datasets.items()}

    with open(FTU_TO_DATASETS, "w") as output:
        json.dump(ftu_to_datasets, output, indent=4)

    metadata = apply_doi_overrides(metadata)
    metadata_by_dataset = metadata.drop_duplicates("dataset_id").set_index(
        "dataset_id", drop=False
    )

    used_dataset_ids = {
        d
        for ids in ftu_to_datasets.values()
        for d in ids
        if d in metadata_by_dataset.index
    }
    doi_metadata = get_doi_metadata(
        metadata_by_dataset.loc[sorted(used_dataset_ids), "publication"]
        .map(clean)
        .dropna()
    )

    graph_list = []
    for ftu, dataset_ids in ftu_to_datasets.items():
        suffix = ftu.rsplit("/", 1)[-1]
        data_sources = [
            build_data_source(
                metadata_by_dataset.loc[dataset_id],
                dataset_id,
                suffix,
                tool_and_cts_by_dataset[dataset_id][0],
                doi_metadata,
            )
            for dataset_id in dataset_ids
            if dataset_id in used_dataset_ids
        ]
        graph_list.append(
            {
                "@id": ftu,
                "@type": "FtuIllustration",
                "data_sources": data_sources,
            }
        )

    out_json_ld["@graph"] = graph_list

    print(f"Now saving to {FTU_DATASETS_OUTPUT}")
    with open(FTU_DATASETS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out_json_ld, f, ensure_ascii=False, indent=4)


def main():
    metadata = load_dataset_metadata()
    build_ftu_datasets_jsonld(metadata=metadata)


if __name__ == "__main__":
    main()
