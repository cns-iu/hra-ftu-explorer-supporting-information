# Code for downloading, preprocessing, and compiling cell type populations for the FTU Explorer and FTU2 paper

This document outlines the code pieces that are needed to source high-quality cell type populations and biomarker expressions for FTU illustrations in the FTU Explorer. These may be implemented either as Jupyter Notebooks or with Python and driver code in Bash, like the Download and Cell Type Annotation (DCTA) and RUI to Compile CTpop (RUI2CTpop) Workflows in [HRApop](https://www.biorxiv.org/content/10.1101/2025.08.14.670406).

## Open questions and notes

- To be added to the FTU Explorer, a cell type populations have to fulfill these criteria:
  - It has to be from a dataset from an organ with an FTU.
  - The CT has to exclusive to an FTU, i.e., it must be:
    - in the FTU illustration and
    - only be connected to the FTU or a child of the FTU in the ASCT+B table for the organ from where the dataset comes
  - It has to be RUI registered, unless it is from the skin, which only has 1 AS. The query at [https://apps.humanatlas.io/api/grlc/hra-pop.html#get-/datasets-with-ftu](https://apps.humanatlas.io/api/grlc/hra-pop.html#get-/datasets-with-ftu) returns datasets that collide with an AS that has an FTU in it. 
  - The CT has to be crosswalked. We can only use cell type populations for crosswalked CTs for the FTU Explorer, because all the CTs in the FTU illustrations are crosswalked. 

## What the FTU Explorer Needs

The FTU Explorer needs two data products to display cell by gene data for its FTU illustrations:

- Cell type populations, which display the number of cells per cell type and the mean biomarkers expression for that CT and data. This has to be deposited at [https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-cell-summaries.jsonld](https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-cell-summaries.jsonld). Te format looks like this:

```json
  "@graph": [
    {
      "@type": "CellSummary",
      "cell_source": "https://doi.org/10.1038/s41467-021-22368-w#CellSummary_kidney-nephron",
      "annotation_method": "Aggregation",
      "biomarker_type": "gene",
      "summary": [
        {
          "@type": "CellSummaryRow",
          "cell_id": "http://purl.obolibrary.org/obo/CL_4030009",
          "cell_label": "epithelial cell of proximal tubule",
          "genes": [
            {
              "@type": "GeneExpression",
              "ensemble_id": "ENSG00000167107",
              "gene_id": "HGNC:26101",
              "gene_label": "ACSF2",
              "mean_expression": 0.24667667
            },
            {
              "@type": "GeneExpression",
              "ensemble_id": "ENSG00000183747",
              "gene_id": "HGNC:32017",
              "gene_label": "ACSM2A",
              "mean_expression": 0.6900019
            },
```

- Metadata about the datasets used, such as author names. This has to be deposited at [https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-datasets.jsonld](https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-datasets.jsonld). The format looks like this:

```json
  "@graph": [
    {
      "@id": "https://purl.humanatlas.io/2d-ftu/kidney-nephron",
      "@type": "FtuIllustration",
      "data_sources": [
        {
          "@id": "https://doi.org/10.1038/s41467-021-22368-w#CellSummary_kidney-nephron",
          "@type": "Dataset",
          "label": "snRNA-seq of Three Healthy Human Kidney Tissue",
          "link": "https://doi.org/10.1038/s41467-021-22368-w",
          "description": "Single cell transcriptional and chromatin accessibility profiling redefine cellular heterogeneity in the adult human kidney",
          "year": 2021,
          "authors": [
            "Yoshiharu Muto",
            "Parker C. Wilson",
            "Nicolas Ledru",
            "Haojia Wu",
            "Henrik Dimke",
            "Sushrut S. Waikar",
            "Benjamin D .Humphreys"
          ]
        }
      ]
    },
```

## Code overview

The FTU2 code consists of six Python scripts that are run in sequence via a `bash` script callded `run_all.sh`:

1. `00-shared.py` defines common functions (e.g., making web requests) and sets variables used across the workflow. It also compiles a list of cell types only found in FTUs, validated against ASCT+B tables.
2. `10-hra-pop-preprocessing-cell-type-population.py`
3. `20-hra-pop-preprocessing-metadata.py`
4. `30-anatomogram-preprcossing-cell-type-population.py` downloads anatomogram data from the [Single-Cell Expression Atlas (SCEA)](https://www.ebi.ac.uk/gxa/sc/home), extracts cells and biomarkers expressions from cells, ad transforms them into a ds-graph format (see "ds-graph" entry in [HRA KG paper](https://www.nature.com/articles/s41597-025-05183-6/tables/1)).
5. `50-anatomogram-preprocessing-metadata.py` extracts donor data from experimental design files obtained from the SCEA.

6. `60-combine-all.py` (driver script) takes cell type populations and metadata from anatomogram and HRApop and makes them available for the [assets folder](https://github.com/hubmapconsortium/hra-ui/tree/main/apps/ftu-ui/src/assets/TEMP) of the FTU Explorer.

7. `run_all` executes all scripts in sequence.

## Pseudocode

### `10-shared.py`

```python

import requests
# OTHER IMPORT STATEMENTS

def download(url:str):
  # add implementation

def get_organs_with_ftus():
  # ADD IMPLEMENTATION
  # uses SPARQL query at https://apps.humanatlas.io/api/grlc/hra.html#get-/2d-ftu-parts to get a list of organs and FTUs, like:
  organs_with_ftus = [
    {
      'organ_label': 'kidney',
      'organ_iri':'UBERON:0002113',
      'ftu':[
        {
          'ftu_iri':'http://purl.obolibrary.org/obo/UBERON_0001285',
          'ftu_digital_object','https://purl.humanatlas.io/2d-ftu/kidney-nephron'
        },
        {
          'ftu_iri':'http://purl.obolibrary.org/obo/UBERON_0004204',
          'ftu_digital_object','https://purl.humanatlas.io/2d-ftu/kidney-outer-medullary-collecting-duct'
        },

        # ADD OTHER ORGANS AND THEIR FTUs

      ]
    }
  ]
  

def compile_cell_types_per_ftu():

  # initialize a dictionary to capture AS-CT combinations from FTU illustrations that only occur in these FTUs
  ftu_cell_types = []

  # download 2d-ftu DOs and get FTU-CT combination
  kg_data = requests.get(url='https://lod.humanatlas.io/2d-ftu')
  purls = [item['@id'].replace('lod','purl') for item in kg_data['@graph']] # purl gets JSON records, lod get metadata

  # Initialize empty list to capture FTU data from HRA KG
  ftu_data = []

  for purl in purls: # loop through PURLs and get FTU data one by one
    ftu_data.append(requests.get(url=purl))

  # loop through ftu_data and isolate cells per FTU
  for ftu in ftu_data:
    data_to_add = {
      'representation_of':ftu['data']['representation_of'],
      'iri':ftu['iri'],
      'cell_types_illustration':{} # note that this is a set
    }

    for node in ftu['data']['illustration_node']:
      cell_types_illustration['cell_types_illustration'].append((node['node_group'], node['representation_of']))

     ftu_cell_types.append(data_to_add)
```

When done, this looks like:

```python

  ftu_cell_types = [
    {
       'representation_of':'UBERON:0004193',
       'iri':'https://purl.humanatlas.io/2d-ftu/kidney-ascending-thin-loop-of-henle'
        'cell_types_illustration':[
          ('Ascending_Thin_Limb_Cell','CL:1001107'), # we capture CT labels and CL IDs as tuples
          ('Ascending_Vasa_Recta','CL:1001131'),
          # PLUS ALL OTHER TUPLES
        ],
        'cell_types_illustration_only':[] # we check below if this CT only occurs in the FTU or elsewhere
    },
    # PLUS DICT FOR ALL OTHER FTUs
  ]

```

Then, we check these FTU-CT pairs against the same AS-CT pairs in the ASCT+B tables to see if they ONLY occur in the FTUs. Some of the code parts here could be modularized into their own functions:

```python

  asctb_cell_types = []

  # download 2d-ftu DOs and get FTU-CT combination
  kg_data = requests.get(url='https://lod.humanatlas.io/asct-b')

  # LOOP THROUGH '@id's and get ASCT+B table data

  # LOOP THROUGH THE CELL TYPES IN ftu_cell_types AND CHECK if the CT in the ASCT+B table see if they are connected to anything other than the FTU or a child of the FTU
  for ftu in ftu_cell_types:
    for cell_type in ftu['cell_types_illustration']:
      if cell_type != IS_LOCATED_IN_OTHER_AS_THAT_IS_NOT(ftu['representation_of']):
        ftu['cell_types_illustration_only'].append(cell_type) # appending the enture tuple if the CT is unique to the FTU

  # Finalize
```
At the end, we should have something like the below, which can then be used to make sure we only use CTs from the high-quality experiemental data from HRApop and anatomogram that occur only in the FTU (skin is an exception, because it only has 1 AS): 
```python

  ftu_cell_types = [
    {
       'representation_of':'UBERON:0004193',
       'iri':'https://purl.humanatlas.io/2d-ftu/kidney-ascending-thin-loop-of-henle'
        'cell_types_illustration':[
          ('Ascending_Thin_Limb_Cell','CL:1001107'), # we capture CT labels and CL IDs as tuples
          ('Ascending_Vasa_Recta','CL:1001131'),
          # PLUS ALL OTHER TUPLES
        ],
        'cell_types_illustration_only':[
          ('Ascending_Thin_Limb_Cell','CL:1001107')
        ] # we check below if this CT only occurs in the FTU or elsewhere
    },
    # PLUS DICT FOR ALL OTHER FTUs
  ]
```

### `20-hra-pop-preprocessing-cell-type-population.py`

Here, we first get cell type populations from the the HRApop Universe at [https://github.com/x-atlas-consortia/hra-pop/tree/main/input-data/v1.0](https://github.com/x-atlas-consortia/hra-pop/tree/main/input-data/v1.0) and from the HRApop Atlas at [https://apps.humanatlas.io/kg-explorer/graph/hra-pop/latest](https://apps.humanatlas.io/kg-explorer/graph/hra-pop/latest).

```python

# universe
hra_pop_universe_cell_type_populations = download(url='https://github.com/x-atlas-consortia/hra-pop/raw/refs/heads/main/input-data/v1.0/sc-transcriptomics-cell-summaries.jsonl.gz')

hra_pop_universe_dataset_metadata = download(url='https://github.com/x-atlas-consortia/hra-pop/raw/refs/heads/main/input-data/v1.0/sc-transcriptomics-dataset-metadata.csv')

# atlas
hra_pop_atlas_cell_type_populations = download(url='https://cdn.humanatlas.io/digital-objects/graph/hra-pop/v1.0/assets/atlas-enriched-dataset-graph.jsonld')

```

Then, we process them into the data format that the FTU Explorer needs, see [the spec above](#what-the-ftu-explorer-needs). Universe data comes in this format:

```json
{
  "@type": "CellSummary",
  "annotation_method": "celltypist",
  "modality": "sc_transcriptomics",
  "cell_source": "https://entity.api.hubmapconsortium.org/entities/f6eb890063d13698feb11d39fa61e45a",
  "summary": [
    {
      "cell_id": "ASCTB-TEMP:proximal-progenitor",
      "cell_label": "Proximal progenitor",
      "gene_expr": [
        {
          "gene_id": "HGNC:18592",
          "gene_label": "NEK10",
          "ensembl_id": "ENSG00000163491.16",
          "mean_gene_expr_value": 1.0049114227294922
        },
        {
          "gene_id": "HGNC:12540",
          "gene_label": "UGT1A8",
          "ensembl_id": "ENSG00000242366.3",
          "mean_gene_expr_value": 0.792599081993103
        },
        {
          "gene_id": "HGNC:8995",
          "gene_label": "PIP5K1B",
          "ensembl_id": "ENSG00000107242.20",
          "mean_gene_expr_value": 1.6220433712005615
        }
        #
        ...
        ...
        ...
        # showing 10 Bs total
      ],
      "count": 64,
      "@type": "CellSummaryRow",
      "percentage": 0.010666666666666666
  }
```

First, we need to check if any cell type population has is from an organ that has an FTU:

```python

for 

```

If yes, we need to check if any cell type population contains cell types only found in any FTUs for that organ:

```python

```

Atlas comes in this format:

MUST be from HRApop Atlas OR for proteomics that has cut-outs for FTUs
Use https://apps.humanatlas.io/api/grlc/hra-pop.html#get-/cell-types-per-dataset
Or https://cdn.humanatlas.io/digital-objects/graph/hra-pop/v1.0/assets/atlas-enriched-dataset-graph.jsonld

MUST be from an organ for which we have 2d-ftu
Can also use https://apps.humanatlas.io/api/grlc/hra-pop.html#get-/datasets-with-ftu
Check for AS collisions, check if FTUs are children
Or https://apps.humanatlas.io/api/grlc/hra-pop.html#get-/datasets-with-maybe-ftu (has optional clause but former should be subset of latter)
Also queries at https://apps.humanatlas.io/api/grlc/hra-scratch.html

Then:

- Get a data frame of FTUs and cells that are only found in these from ASCTB+ tables via HRA KG
- Get datasets with FTUs in them from [https://apps.humanatlas.io/api/grlc/hra-pop.html#get-/datasets-with-ftu](https://apps.humanatlas.io/api/grlc/hra-pop.html#get-/datasets-with-ftu)
- Check for CTs, check if those only occur in FTUs (via ASCT+B table)
- Can use [https://apps.humanatlas.io/kg-explorer/graph/2d-ftu-illustrations/latest](https://apps.humanatlas.io/kg-explorer/graph/2d-ftu-illustrations/latest) to tell which CTs are in FTU. Also check for children in AS partonomy that are NOT FTUs whether those have the CT

These are ds-graph DOs and look like:

```json

 {
        "@id": "https://entity.api.hubmapconsortium.org/entities/1628b6f7eb615862322d6274a6bc9fa0",
      "@type": "Donor",
      "samples": [
        {
          "@id": "https://entity.api.hubmapconsortium.org/entities/0b43d8d0dbbc5e3923a8b963650ab8e3",
          "@type": "Sample",
          "datasets": [],
          "sections": [
            {
              "@id": "https://entity.api.hubmapconsortium.org/entities/35e16f13caab262f446836f63cf4ad42",
              "@type": "Sample",
              "datasets": [
                {
                  "@id": "https://entity.api.hubmapconsortium.org/entities/3de525fe3e5718f297e8d62e037a042d",
                  "@type": "Dataset",
                  "link": "https://portal.hubmapconsortium.org/browse/dataset/3de525fe3e5718f297e8d62e037a042d",
                  "technology": "RNAseq",
                  "cell_count": "6000",
                  "gene_count": "60286",
                  "organ_id": "http://purl.obolibrary.org/obo/UBERON_0002108",
                  "label": "Registered 11/3/2023, HuBMAP Process, TMC-Stanford",
                  "description": "Dataset Type: RNAseq [Salmon]",
                  "thumbnail": "assets/icons/ico-unknown.svg",
                  "summaries": [
                    {
                      "@type": "CellSummary",
                      "annotation_method": "celltypist",
                      "modality": "sc_transcriptomics",
                      "summary": [
                        {
                          "cell_id": "ASCTB-TEMP:enterocyte",
                          "cell_label": "Enterocyte",
                          "gene_expr": [
                           ...
                          ],
                          "count": 3600,
                          "@type": "CellSummaryRow",
                          "percentage": 0.6
                        },
                        {
                          "cell_id": "ASCTB-TEMP:paneth",
                          "cell_label": "Paneth",
                          "gene_expr": [
                            ...
                            ],
                          "count": 265,
                          "@type": "CellSummaryRow",
                          "percentage": 0.04416666666666667
                        },

```

### `30-hra-pop-preprocessing-metadata.py`

### `40-anatomogram-preprcossing-cell-type-population.py`

The `organ_metadata` list contains dictionaries with downloads links and IDs for kidney, liver, lung, and pancreas.

```python

organ_metadata = [
    {
        'name': 'kidney',
        'url_counts': 'https://www.ebi.ac.uk/gxa/sc/experiment/E-CURD-119/download/zip?fileType=normalised',
        'url_experimental_design': 'https://www.ebi.ac.uk/gxa/sc/experiment/E-CURD-119/download?fileType=experiment-design',
        'experiment_id': 'E-CURD-119'
    },
    {
        'name': 'liver',
        'url_counts': 'https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-10553/download/zip?fileType=normalised',
        'url_experimental_design': 'https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-10553/download?fileType=experiment-design',
        'experiment_id': 'E-MTAB-10553'
    },
    {
        'name': 'lung',
        'url_counts': 'https://www.ebi.ac.uk/gxa/sc/experiment/E-GEOD-130148/download/zip?fileType=normalised',
        'url_experimental_design': 'https://www.ebi.ac.uk/gxa/sc/experiment/E-GEOD-130148/download?fileType=experiment-design',
        'experiment_id': 'E-GEOD-130148'
    },
    {
        'name': 'pancreas',
        'url_counts': 'https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-5061/download/zip?fileType=normalised',
        'url_experimental_design': 'https://www.ebi.ac.uk/gxa/sc/experiment/E-MTAB-5061/download?fileType=experiment-design',
        'experiment_id': 'E-MTAB-5061'
    }
]
```

Then, we define functions that handle the data download:

First, a function to download a file to a folder from a given URL:

```python

def download_file(url:str, file_name:str, sub_folder_name:str):
  """Downloads

  Args:
      url (str): URL for file download
      file_name (str): file name
      subfolder_name (str): subfolder name
  """

  # IMPLEMENTATION GOES HERE
```

A function to unzip a downloaded ZIP file to a target folder:

```python
def unzip_to_folder(file_path: str, target_folder: str):
    """
    Unzip the file at the specified file_path into target_folder,
    but only if the folder is empty.

    Args:
        file_path (str): Path to the .zip (or other archive) file.
        target_folder (str): Path where the archive should be extracted.
    """

    # IMPLEMENTATION GOES HERE
    ...
```

And finally a driver function that calls the other two:

```python

def download_anatomogram_data(url_counts:str, url_experiment:str, experiment_name:str, organ_name:str):
  """Download and unzip anatomogram data for a given organ.

    Args:
        url_counts (str): The URL to download the data from.
        url_experiment (str): The URL to download the experimental metadata from.
        url_experiment (str): The name for the experimental design file.
        organ_name (str): The name of the organ (used for file and folder names).
  """
  download_file(url_counts, f'{organ_name}.zip', f'{organ_name}') # downloads cell by gene matrix
  download_file(url_experiment, f'{experiment_name}.tsv', f'{organ_name}')  # download experimental design file with metadata
  unzip_to_folder(f'data/{organ_name}/{organ_name}.zip', f'data/{organ_name}') # unzips cell by gene matrix folder

  # REST OF IMPLEMENTATION GOES HERE
```

Then, we use these functions to download all anatomogram data:

```python

for organ in organ_metadata:
  download_anatomogram_data(
      organ['url_counts'],
      organ['url_experimental_design'],
      organ['experiment_id'],
      organ['name']
  )

```

Next we process the downloaded data. Exemplarily shown is kidney, but this will be automatized then run over all organs in `organ_metadata`:

```python
anndata_kidney = sc.read_mtx('data/kidney/E-CURD-119.aggregated_filtered_normalised_counts.mtx')
df_kidney = anndata_kidney.to_df()
```

This returns a data frame from the `anndata` oibject that contains biomarkers in rows and cell instances in colums. The values are biomarker expressions:

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }

</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>0</th>
      <th>1</th>
      <th>2</th>
      <th>3</th>
      <th>4</th>
      <th>5</th>
      <th>6</th>
      <th>7</th>
      <th>8</th>
      <th>9</th>
      <th>...</th>
      <th>30579</th>
      <th>30580</th>
      <th>30581</th>
      <th>30582</th>
      <th>30583</th>
      <th>30584</th>
      <th>30585</th>
      <th>30586</th>
      <th>30587</th>
      <th>30588</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.000000</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>...</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.000000</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.000000</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>...</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.000000</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>96.007149</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>...</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.000000</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
      <td>0.0</td>
    </tr>
  </tbody>
</table>
<p>38917 rows × 30589 columns</p>
</div>

Then, we load genes and cell type information for kidney, which gives:

```python
rows_kidney = pd.read_csv('data/kidney/E-CURD-119.aggregated_filtered_normalised_counts.mtx_rows',names=['col1', 'col2'], sep='\t').drop(['col2'], axis=1)

cols_kidney = pd.read_csv('data/kidney/E-CURD-119.aggregated_filtered_normalised_counts.mtx_cols', names=['col1'])
```

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }

</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>col1</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>ENSG00000000003</td>
    </tr>
    <tr>
      <th>1</th>
      <td>ENSG00000000005</td>
    </tr>
    <tr>
      <th>2</th>
      <td>ENSG00000000419</td>
    </tr>
    <tr>
      <th>3</th>
      <td>ENSG00000000457</td>
    </tr>
    <tr>
      <th>4</th>
      <td>ENSG00000000460</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
    </tr>
    <tr>
      <th>38912</th>
      <td>ENSG00000290147</td>
    </tr>
    <tr>
      <th>38913</th>
      <td>ENSG00000290149</td>
    </tr>
    <tr>
      <th>38914</th>
      <td>ENSG00000290163</td>
    </tr>
    <tr>
      <th>38915</th>
      <td>ENSG00000290164</td>
    </tr>
    <tr>
      <th>38916</th>
      <td>ENSG00000290165</td>
    </tr>
  </tbody>
</table>
<p>38917 rows × 1 columns</p>
</div>

Folowing that, we load experiental design data for the kidney:

```python
ref_data_kidney = pd.read_csv('../../ref_data/Anatomogram/count-files/ExpDesign-E-CURD-119.tsv', sep = '\t')

```

Which gives:

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }

</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Assay</th>
      <th>Sample Characteristic[organism]</th>
      <th>Sample Characteristic Ontology Term[organism]</th>
      <th>Sample Characteristic[individual]</th>
      <th>Sample Characteristic Ontology Term[individual]</th>
      <th>Sample Characteristic[ethnic group]</th>
      <th>Sample Characteristic Ontology Term[ethnic group]</th>
      <th>Sample Characteristic[sex]</th>
      <th>Sample Characteristic Ontology Term[sex]</th>
      <th>Sample Characteristic[age]</th>
      <th>...</th>
      <th>Sample Characteristic[organism part]</th>
      <th>Sample Characteristic Ontology Term[organism part]</th>
      <th>Sample Characteristic[clinical information]</th>
      <th>Sample Characteristic Ontology Term[clinical information]</th>
      <th>Factor Value[sex]</th>
      <th>Factor Value Ontology Term[sex]</th>
      <th>Factor Value[inferred cell type - ontology labels]</th>
      <th>Factor Value Ontology Term[inferred cell type - ontology labels]</th>
      <th>Factor Value[inferred cell type - authors labels]</th>
      <th>Factor Value Ontology Term[inferred cell type - authors labels]</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>SAMN15040593-AAACCTGAGGACATTA</td>
      <td>Homo sapiens</td>
      <td>http://purl.obolibrary.org/obo/NCBITaxon_9606</td>
      <td>Healthy5</td>
      <td>NaN</td>
      <td>European</td>
      <td>http://purl.obolibrary.org/obo/HANCESTRO_0005</td>
      <td>female</td>
      <td>http://purl.obolibrary.org/obo/PATO_0000383</td>
      <td>52 year</td>
      <td>...</td>
      <td>cortex of kidney</td>
      <td>http://purl.obolibrary.org/obo/UBERON_0001225</td>
      <td>glomerular filtration rate 98 ml/min/1.73âm2...</td>
      <td>NaN</td>
      <td>female</td>
      <td>http://purl.obolibrary.org/obo/PATO_0000383</td>
      <td>kidney loop of Henle thick ascending limb epit...</td>
      <td>http://purl.obolibrary.org/obo/CL_1001106</td>
      <td>thick ascending limb</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>1</th>
      <td>SAMN15040593-AAACCTGCAGCTCGAC</td>
      <td>Homo sapiens</td>
      <td>http://purl.obolibrary.org/obo/NCBITaxon_9606</td>
      <td>Healthy5</td>
      <td>NaN</td>
      <td>European</td>
      <td>http://purl.obolibrary.org/obo/HANCESTRO_0005</td>
      <td>female</td>
      <td>http://purl.obolibrary.org/obo/PATO_0000383</td>
      <td>52 year</td>
      <td>...</td>
      <td>cortex of kidney</td>
      <td>http://purl.obolibrary.org/obo/UBERON_0001225</td>
      <td>glomerular filtration rate 98 ml/min/1.73âm2...</td>
      <td>NaN</td>
      <td>female</td>
      <td>http://purl.obolibrary.org/obo/PATO_0000383</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>2</th>
      <td>SAMN15040593-AAACCTGCAGTATAAG</td>
      <td>Homo sapiens</td>
      <td>http://purl.obolibrary.org/obo/NCBITaxon_9606</td>
      <td>Healthy5</td>
      <td>NaN</td>
      <td>European</td>
      <td>http://purl.obolibrary.org/obo/HANCESTRO_0005</td>
      <td>female</td>
      <td>http://purl.obolibrary.org/obo/PATO_0000383</td>
      <td>52 year</td>
      <td>...</td>
      <td>cortex of kidney</td>
      <td>http://purl.obolibrary.org/obo/UBERON_0001225</td>
      <td>glomerular filtration rate 98 ml/min/1.73âm2...</td>
      <td>NaN</td>
      <td>female</td>
      <td>http://purl.obolibrary.org/obo/PATO_0000383</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>3</th>
      <td>SAMN15040593-AAACCTGCATGCCTAA</td>
      <td>Homo sapiens</td>
      <td>http://purl.obolibrary.org/obo/NCBITaxon_9606</td>
      <td>Healthy5</td>
      <td>NaN</td>
      <td>European</td>
      <td>http://purl.obolibrary.org/obo/HANCESTRO_0005</td>
      <td>female</td>
      <td>http://purl.obolibrary.org/obo/PATO_0000383</td>
      <td>52 year</td>
      <td>...</td>
      <td>cortex of kidney</td>
      <td>http://purl.obolibrary.org/obo/UBERON_0001225</td>
      <td>glomerular filtration rate 98 ml/min/1.73âm2...</td>
      <td>NaN</td>
      <td>female</td>
      <td>http://purl.obolibrary.org/obo/PATO_0000383</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>4</th>
      <td>SAMN15040593-AAACCTGGTATAGTAG</td>
      <td>Homo sapiens</td>
      <td>http://purl.obolibrary.org/obo/NCBITaxon_9606</td>
      <td>Healthy5</td>
      <td>NaN</td>
      <td>European</td>
      <td>http://purl.obolibrary.org/obo/HANCESTRO_0005</td>
      <td>female</td>
      <td>http://purl.obolibrary.org/obo/PATO_0000383</td>
      <td>52 year</td>
      <td>...</td>
      <td>cortex of kidney</td>
      <td>http://purl.obolibrary.org/obo/UBERON_0001225</td>
      <td>glomerular filtration rate 98 ml/min/1.73âm2...</td>
      <td>NaN</td>
      <td>female</td>
      <td>http://purl.obolibrary.org/obo/PATO_0000383</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
  </tbody>
</table>
<p>5 rows × 25 columns</p>
</div>

From there, we extract cell type per cell:

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }

</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Assay</th>
      <th>Cell_Type</th>
      <th>CL_ID</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>SAMN15040593-AAACCTGAGGACATTA</td>
      <td>thick ascending limb</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>1</th>
      <td>SAMN15040593-AAACCTGCAGCTCGAC</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>2</th>
      <td>SAMN15040593-AAACCTGCAGTATAAG</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>3</th>
      <td>SAMN15040593-AAACCTGCATGCCTAA</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>4</th>
      <td>SAMN15040593-AAACCTGGTATAGTAG</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>30584</th>
      <td>SAMN15040597-TTTGTCATCACAGGCC</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>30585</th>
      <td>SAMN15040597-TTTGTCATCACCAGGC</td>
      <td>NaN</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>30586</th>
      <td>SAMN15040597-TTTGTCATCACCGTAA</td>
      <td>connecting tubule</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>30587</th>
      <td>SAMN15040597-TTTGTCATCCTACAGA</td>
      <td>distal convoluted tubule 1</td>
      <td>UBERON:0001292</td>
    </tr>
    <tr>
      <th>30588</th>
      <td>SAMN15040597-TTTGTCATCGGCGCTA</td>
      <td>distal convoluted tubule 1</td>
      <td>UBERON:0001292</td>
    </tr>
  </tbody>
</table>
<p>30589 rows × 3 columns</p>
</div>

At the end, we have a link between columns and cell type label (from CL):

```
                             col1
0            thick ascending limb
1                             NaN
2                             NaN
3                             NaN
4                             NaN
...                           ...
30584                         NaN
30585                         NaN
30586           connecting tubule
30587  distal convoluted tubule 1
30588  distal convoluted tubule 1

[30589 rows x 1 columns]
```

Then, we convert the dataframe for each organ to `anndata` for analysis to support average gene expression via `scanpy.rank_gene_groups()`

```python

```

Next, the mean gene ecression per cell type and dataset needs to be computed:

Then, we repeat that for the other three organs.

### `50-anatomogram-preprocessing-metadata.py`

### `60-combine-all.py`

Deploys:

- Cell summaries: https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-cell-summaries.jsonld
- Metadata: https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-datasets.jsonld
- Might build FTU explorer ds-graph, could be delivered via HRA API. Like https://apps.humanatlas.io/kg-explorer/ds-graph/hubmap/latest

For testing, generate as format: https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-cell-summaries.jsonld
Web component/widget has two input, one for cell summaries (https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-cell-summaries.jsonld) and one for datasets (https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-datasets.jsonld)

### `run_all.sh`
Runs all Pythons scripts.

# Implementation details
- How should we handle cell summaries in the FTU Explorer for which we have no associated paper? This applies to many HuBMAP and SenNet datasets. The Explorer needs to display metadata in the bottom right corner. Can we invent new table headers that work for cell summaries and papers?
- Use `gitgnore` for big files
- `output` for usage, raw-data` folder for downloaded data