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


def handle_anatomogram_data():
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

    metadata_json = [
        {
            "name": "kidney",
            "url_counts": "https://www.ebi.ac.uk/gxa/sc/experiment/E-CURD-119/download/zip?fileType=normalised",
            "url_experimental_design": "https://www.ebi.ac.uk/gxa/sc/experiment/E-CURD-119/download?fileType=experiment-design",
            "experiment_id": "E-CURD-119",
        },
        {
            "name": "liver",
            "url_counts": "https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-10553/download/zip?fileType=normalised",
            "url_experimental_design": "https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-10553/download?fileType=experiment-design",
            "experiment_id": "E-MTAB-10553",
        },
        {
            "name": "lung",
            "url_counts": "https://www.ebi.ac.uk/gxa/sc/experiment/E-GEOD-130148/download/zip?fileType=normalised",
            "url_experimental_design": "https://www.ebi.ac.uk/gxa/sc/experiment/E-GEOD-130148/download?fileType=experiment-design",
            "experiment_id": "E-GEOD-130148",
        },
        {
            "name": "pancreas",
            "url_counts": "https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-5061/download/zip?fileType=normalised",
            "url_experimental_design": "https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-5061/download?fileType=experiment-design",
            "experiment_id": "E-MTAB-5061",
        },
    ]

    for organ in metadata_json:
        download_and_unzip_anatomogram_data(
            organ["url_counts"],
            organ["url_experimental_design"],
            organ["experiment_id"],
            organ["name"],
        )


def main():
    # Driver code

    handle_anatomogram_data()


# You may want to use/crib off of the summary generator in the DCTA workflow:
# https://github.com/hubmapconsortium/hra-workflows/blob/main/containers/extract-summary/context/main.py#L95

# Also the gene expression container might be useful too
# https://github.com/hubmapconsortium/hra-workflows/blob/main/containers/gene-expression/context/main.py

# Sure. Yeah, one way to do this is to format the anatomograms as one h5ad dataset per ftu and then use the exact some processing as was done for HRApop on those.

# Yeah, I think it'd make total sense to format the anatogram data like the HRApop input data. It should be easy enough to format the cell summaries in json lines format like you've been parsing and write a dataset metadata csv like we have on HRApop for that data. We can then easily add it to HRApop or just simplify your FTU workflow.

if __name__ == "__main__":
    main()
