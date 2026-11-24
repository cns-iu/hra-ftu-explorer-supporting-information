# Anatomogram and CTann cell-type comparison

This directory contains the analyses used to compare Anatomogram author cell-type annotations with HRApop and CTann annotations. The workflow is divided into two tasks, with three Python scripts per task.

## Repository layout

The commands below assume the following repository structure:

```text
hra-ftu-explorer-supporting-information/
├── anatomogram-comparison/
│   ├── README.md
│   ├── requirements.txt
│   ├── scripts/
│   └── outputs/
└── anatomogram-data/
    ├── anatomogram-sc-transcriptomics-cell-instances.csv.gz
    ├── anatomogram-sc-transcriptomics-cell-summaries.jsonl.gz
    └── ctann-supertree.csv
```

The first two files under `anatomogram-data` are already present in the repository. Task 2 also requires the latest reviewed CTann supertree CSV. Copy that file to `anatomogram-data/ctann-supertree.csv`, or replace the supertree path in the command with its actual location.

## Setup

Run all commands from the repository root:

```bash
cd /path/to/hra-ftu-explorer-supporting-information
```

Create and activate a virtual environment if needed:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r anatomogram-comparison/requirements.txt
```

If an existing Python or Conda environment already provides the required packages, only the final installation command is needed.

Required packages:

- pandas 2.0 or newer
- NumPy 1.24 or newer
- Matplotlib 3.7 or newer

## Input files

The workflow uses these paths relative to the repository root:

```text
anatomogram-data/anatomogram-sc-transcriptomics-cell-instances.csv.gz
anatomogram-data/anatomogram-sc-transcriptomics-cell-summaries.jsonl.gz
anatomogram-data/ctann-supertree.csv
```

The scripts create their output directories automatically.

## Method definitions

- The Task 1 set comparison uses CellTypist, Azimuth, popV, and FR-Match.
- Pan-Human Azimuth is excluded.
- FR-Match is available only for the lung datasets.
- The supplementary cell-count script currently follows the original comparison definition and plots CellTypist, Azimuth, and popV.
- FR-Match cannot be included in the Task 2 paired-cell analysis until a numeric-identifier-to-cell-barcode crosswalk is available.
- Strict and ontology-aware denominators contain paired cells with valid CL identifiers on both sides.
- Valid CL identifiers absent from the supplied supertree are retained as `Unmapped`.
- Provisional non-CL author identifiers are reported separately.

## Task 1: Anatomogram versus HRApop

Task 1 compares exact CL identifiers and cell counts between the Anatomogram author annotations and HRApop.

### 1. Generate the cell-count comparison

```bash
python3 anatomogram-comparison/scripts/task_01_anatomogram_hrapop/01_cell_counts_per_ct.py \
  --instances anatomogram-data/anatomogram-sc-transcriptomics-cell-instances.csv.gz \
  --summaries anatomogram-data/anatomogram-sc-transcriptomics-cell-summaries.jsonl.gz \
  --output-dir anatomogram-comparison/outputs/task_01_anatomogram_hrapop
```

This script writes its tables to:

```text
anatomogram-comparison/outputs/task_01_anatomogram_hrapop/tables/cell_counts/
```

It writes the cell-count figure in PNG, PDF, and SVG formats to:

```text
anatomogram-comparison/outputs/task_01_anatomogram_hrapop/figures/
```

### 2. Compare the Anatomogram and HRApop CL-ID sets

```bash
python3 anatomogram-comparison/scripts/task_01_anatomogram_hrapop/02_compare_cell_type_sets.py \
  --instances anatomogram-data/anatomogram-sc-transcriptomics-cell-instances.csv.gz \
  --summaries anatomogram-data/anatomogram-sc-transcriptomics-cell-summaries.jsonl.gz \
  --output-dir anatomogram-comparison/outputs/task_01_anatomogram_hrapop/tables
```

This step generates the source-specific counts, shared and source-specific CL-ID categories, provisional identifier report, selected plotting terms, and QC summary.

### 3. Generate the Task 1 set-comparison figure

```bash
python3 anatomogram-comparison/scripts/task_01_anatomogram_hrapop/03_plot_cell_type_comparison.py \
  --tables-dir anatomogram-comparison/outputs/task_01_anatomogram_hrapop/tables \
  --output-dir anatomogram-comparison/outputs/task_01_anatomogram_hrapop/figures
```

Task 1 should be run in the order shown above. Scripts 2 and 3 form a direct analysis-to-figure sequence. Script 1 is an independent supplementary cell-count analysis that uses the same source inputs.

## Task 2: Ontology-aware author versus CTann comparison

Task 2 pairs author and CTann annotations at the cell level, calculates strict exact CL-ID agreement, and then classifies nonidentical annotations using the CTann supertree.

### 1. Prepare paired author and CTann annotations

```bash
python3 anatomogram-comparison/scripts/task_02_author_ctann_supertree/01_prepare_author_ctann_pairs.py \
  --instances anatomogram-data/anatomogram-sc-transcriptomics-cell-instances.csv.gz \
  --output-dir anatomogram-comparison/outputs/task_02_author_ctann_supertree/tables/strict
```

### 2. Classify paired annotations using the supertree

Confirm that the supertree exists before running this step:

```bash
test -f anatomogram-data/ctann-supertree.csv
```

Then run:

```bash
python3 anatomogram-comparison/scripts/task_02_author_ctann_supertree/02_classify_supertree_relationships.py \
  --paired-annotations anatomogram-comparison/outputs/task_02_author_ctann_supertree/tables/strict/paired_annotations.csv.gz \
  --supertree anatomogram-data/ctann-supertree.csv \
  --output-dir anatomogram-comparison/outputs/task_02_author_ctann_supertree/tables/ontology
```

The relationship classes are `Exact`, `CTann narrower`, `CTann broader`, `Different branch`, and `Unmapped`.

### 3. Generate the Task 2 figures

```bash
python3 anatomogram-comparison/scripts/task_02_author_ctann_supertree/03_plot_author_ctann_comparison.py \
  --strict-dir anatomogram-comparison/outputs/task_02_author_ctann_supertree/tables/strict \
  --ontology-dir anatomogram-comparison/outputs/task_02_author_ctann_supertree/tables/ontology \
  --output-dir anatomogram-comparison/outputs/task_02_author_ctann_supertree/figures
```

## Expected output structure

After all scripts have completed, the output directory should contain:

```text
anatomogram-comparison/outputs/
├── task_01_anatomogram_hrapop/
│   ├── figures/
│   └── tables/
│       └── cell_counts/
└── task_02_author_ctann_supertree/
    ├── figures/
    └── tables/
        ├── ontology/
        └── strict/
```

The generated tables are the numerical source of truth for the manuscript results and figure labels.

## Troubleshooting

### Run commands from the correct directory

If a command reports that an input file cannot be found, confirm that the terminal is in:

```text
hra-ftu-explorer-supporting-information
```

### Confirm the inputs

```bash
ls -lh anatomogram-data/anatomogram-sc-transcriptomics-cell-instances.csv.gz
ls -lh anatomogram-data/anatomogram-sc-transcriptomics-cell-summaries.jsonl.gz
ls -lh anatomogram-data/ctann-supertree.csv
```

### Confirm the Python environment

```bash
python3 --version
python3 -c "import pandas, numpy, matplotlib; print('Dependencies available')"
```

### Recreate outputs

The scripts overwrite files with the same output names. To regenerate an analysis, rerun its scripts in numerical order.
