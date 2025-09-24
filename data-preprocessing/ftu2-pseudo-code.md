# Code for downloading, preprocessing, and compiling cell type populations for the FTU Explorer and FTU2 paper

This document outlines the code pieces that are needed to source high-quality cell type populations and biomarker expressions for FTU illustrations in the FTU Explorer. These may be implemented either as Jupyter Notebooks or with Python and driver code in Bash, like the Download and Cell Type Annotation (DCTA) and RUI to Compile CTpop (RUI2CTpop) Workflows in [HRApop](https://www.biorxiv.org/content/10.1101/2025.08.14.670406). 

## Open questions

- How should we handle cell summaries in the FTU Explorer for which we have no associated paper? This applies to many HuBMAP and SenNet datasets.  The Explorer needs to display metadata in the bottom right corner.  Can we invent new table headers that work for cell summaries and papers?

## What the FTU Explorer Needs
The FTU Explorer needs two data products to display cell by gene data for its FTU illustrations:
- Cell type populations, which display the number of cells per cell type and the mean biomarkers expression for that CT and data. This has to be deposited at [https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-cell-summaries.jsonld](https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-cell-summaries.jsonld)
- Metadata about the datasets used, such as author names. This has to be deposited at [https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-datasets.jsonld](https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-datasets.jsonld)

## What code we are writing to get that data

The FTU2 code consists of six Python scripts that are run in sequence via a `bash` script callded `run_all.sh`:

### Shared
1. `00-shared.py` sets up shared core functionality, e.g., making web requests and handling `pandas` data frames)

### Handling anatomogram data:
2. `01-anatomogram-preprcossing-cell-type-population.py` downloads anatomogram data from the [Single-Cell Expression Atlas (SCEA)](https://www.ebi.ac.uk/gxa/sc/home), extracts cells and biomarkers expressions from cells, ad transforms them into a ds-graph format (see "ds-graph" entry in [HRA KG paper](https://www.nature.com/articles/s41597-025-05183-6/tables/1)). 
3. `02-anatomogram-preprocessing-metadata.py` extracts donor data from experimental design files obtained from the SCEA. 

### Handling HRAPop Universe Data:
4. `03-hra-pop-preprocessing-cell-type-population.py`
5. `04-hra-pop-preprocessing-metadata.py`

Needs to also use universe data that has right CTs even if not RUI and ALL skin data

### Driver script
6. `05-combine-all.py` takes cell type populations and metadata from anatomogram and HRApop and makes them available for the [assets folder](https://github.com/hubmapconsortium/hra-ui/tree/main/apps/ftu-ui/src/assets/TEMP) of the FTU Explorer. 

## Pseudocode

### `00-shared.py`

### `01-anatomogram-preprcossing-cell-type-population.py`

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
  # Make sure the data folder is present
	...
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

### `02-anatomogram-preprocessing-metadata.py`


### `03-hra-pop-preprocessing-cell-type-population.py`

Here, we first get cell type populations from the the HRApop Universe at [https://github.com/x-atlas-consortia/hra-pop/tree/main/input-data/v1.0](https://github.com/x-atlas-consortia/hra-pop/tree/main/input-data/v1.0) and from the HRApop Atlas at [https://apps.humanatlas.io/kg-explorer/graph/hra-pop/latest](https://apps.humanatlas.io/kg-explorer/graph/hra-pop/latest). 

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

### `04-hra-pop-preprocessing-metadata.py`



### `05-combine-all.py`

Deploys:
- Cell summaries: https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-cell-summaries.jsonld 
- Metadata: https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-datasets.jsonld 
- Might build FTU explorer ds-graph, could be delivered via HRA API. Like https://apps.humanatlas.io/kg-explorer/ds-graph/hubmap/latest 

For testing, generate as format: https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-cell-summaries.jsonld 
Web component/widget has two input, one for cell summaries (https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-cell-summaries.jsonld) and one for datasets (https://github.com/hubmapconsortium/hra-ui/blob/main/apps/ftu-ui/src/assets/TEMP/ftu-datasets.jsonld) 