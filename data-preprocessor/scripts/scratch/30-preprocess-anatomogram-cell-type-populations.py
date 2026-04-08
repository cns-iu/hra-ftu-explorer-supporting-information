from shared import *


def download_and_unzip_anatomogram_data(
    url_counts: str, url_experiment: str, experiment_name: str, organ_name: str
):
    """
    Download and extract anatomogram dataset files for a specific organ.

    This function downloads a ZIP archive containing normalized count data and a TSV file
    containing experimental design metadata for a given organ. After downloading, it extracts
    the ZIP archive into the organ's raw data directory.

    Args:
        url_counts (str): URL pointing to the ZIP file with normalized count data.
        url_experiment (str): URL pointing to the experimental design (TSV) file.
        experiment_name (str): The base name for the experimental design file (without extension).
        organ_name (str): The name of the organ (used to create subdirectories and filenames).

    Returns:
        None
            The function performs file download and extraction as side effects,
            saving results under `ANATOMOGRAMN_RAW_DATA / organ_name`.

    Raises:
        requests.HTTPError: If downloading either file fails due to an HTTP error.
        OSError: If writing, saving, or extracting files to disk fails.
    """
    download_from_url(
        url_counts, ANATOMOGRAMN_RAW_DATA / organ_name, f"{organ_name}.zip"
    )
    download_from_url(
        url_experiment, ANATOMOGRAMN_RAW_DATA / organ_name, f"{experiment_name}.tsv"
    )
    unzip_to_folder(
        f"{ANATOMOGRAMN_RAW_DATA}/{organ_name}/{organ_name}.zip",
        f"{ANATOMOGRAMN_RAW_DATA}/{organ_name}",
    )


def download_anatomogram_data(metadata_anatomogram_json: list):
    """
    Download and extract anatomogram datasets for all organs defined in the metadata file.

    This function reads the anatomogram metadata JSON file specified by `ANATOMOGRAMN_METADATA`,
    which contains information about multiple organs and their associated dataset URLs.
    For each organ entry, it downloads the normalized count data (ZIP) and experimental
    design file (TSV), then extracts the ZIP archive into the organ’s raw data directory.

    The function delegates downloading and extraction to `download_and_unzip_anatomogram_data()`.

    Returns:
        None
            Performs file downloads and extractions as side effects; does not return a value.

    Raises:
        FileNotFoundError: If the metadata file `ANATOMOGRAMN_METADATA` cannot be found.
        json.JSONDecodeError: If the metadata file is not valid JSON.
        requests.HTTPError: If any file download fails due to an HTTP error.
        OSError: If there are issues writing or extracting files to disk.
    """
    # Download anatomogram data

    # FROM BRUCE VIA SLACK
    # Yeah, same old scanpy function
    # https://github.com/hubmapconsortium/hra-workflows/blob/main/containers/gene-expression/context/main.py#L43 where n_genes=10000

    for organ in metadata_anatomogram_json:
        download_and_unzip_anatomogram_data(
            organ["url_counts"],
            organ["url_experimental_design"],
            organ["experiment_id"],
            organ["name"],
        )


def extract_cell_type_population(organ_metadata: dict):
    """_summary_

    Args:
        organ_name (str): _description_
    """
    ad = sc.read_mtx(
        ANATOMOGRAMN_RAW_DATA
        / organ_metadata["name"]
        / f"{organ_metadata['experiment_id']}.aggregated_filtered_normalised_counts.mtx"
    )

    df_kidney = ad.to_df()
    pprint(df_kidney.head())

    # Load genes and cell type information
    index_kidney = pd.read_csv(
        ANATOMOGRAMN_RAW_DATA
        / organ_metadata["name"]
        / f"{organ_metadata['experiment_id']}.aggregated_filtered_normalised_counts.mtx_rows",
        names=["col1", "col2"],
        sep="\t",
    )
    cols_kidney = pd.read_csv(
        ANATOMOGRAMN_RAW_DATA
        / organ_metadata["name"]
        / f"{organ_metadata['experiment_id']}.aggregated_filtered_normalised_counts.mtx_cols",
        names=["col1"],
    )

    index_kidney = index_kidney.drop(["col2"], axis=1)
    pprint(index_kidney.head())

    pprint(cols_kidney.head())

    # Load reference data
    ref_data_kidney = pd.read_csv(
        ANATOMOGRAMN_RAW_DATA
        / organ_metadata["name"]
        / f"{organ_metadata['experiment_id']}.tsv",
        sep="\t",
    )
    pprint(ref_data_kidney.head())

    pprint(ref_data_kidney.columns)

    ref_data_kidney = ref_data_kidney.rename(
        columns={
            "Factor Value[inferred cell type - authors labels]": "Cell_Type",
            "Factor Value Ontology Term[inferred cell type - authors labels]": "CL_ID",
        }
    )

    ref_data_mod_kidney = ref_data_kidney[["Assay", "Cell_Type", "CL_ID"]]

    ref_data_mod_kidney["CL_ID"] = ref_data_mod_kidney["CL_ID"].str.split("/").str[-1]

    ref_data_mod_kidney["CL_ID"] = ref_data_mod_kidney["CL_ID"].str.replace("_", ":")

    pprint(ref_data_mod_kidney)

    # Create a mapping using dataframe2
    mapping = ref_data_mod_kidney.set_index("Assay")["Cell_Type"]

    # Use the map function to replace values in dataframe1
    cols_kidney["col1"] = cols_kidney["col1"].map(mapping)

    # Display the modified dataframe1
    print(cols_kidney)

    print(cols_kidney.value_counts())


def main():
    # Driver code

    download_anatomogram_data(anatomogram_files_json)
    extract_cell_type_population(anatomogram_files_json[0])


# You may want to use/crib off of the summary generator in the DCTA workflow:
# https://github.com/hubmapconsortium/hra-workflows/blob/main/containers/extract-summary/context/main.py#L95

# Also the gene expression container might be useful too
# https://github.com/hubmapconsortium/hra-workflows/blob/main/containers/gene-expression/context/main.py

# Sure. Yeah, one way to do this is to format the anatomograms as one h5ad dataset per ftu and then use the exact some processing as was done for HRApop on those.

# Yeah, I think it'd make total sense to format the anatogram data like the HRApop input data. It should be easy enough to format the cell summaries in json lines format like you've been parsing and write a dataset metadata csv like we have on HRApop for that data. We can then easily add it to HRApop or just simplify your FTU workflow.

if __name__ == "__main__":
    main()
