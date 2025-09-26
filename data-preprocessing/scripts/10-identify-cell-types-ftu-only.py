from shared import *

s = {
 "@graph": [
    {
      "@type": "CellSummary",
      "cell_source": "https://doi.org/10.1038/s41467-021-22368-w#CellSummary_kidney-nephron",
      "annotation_method": "Aggregation",
      "biomarker_type": "gene",
      "summary":""
      }]
}

r = requests.get('https://apps.humanatlas.io/hra-api/v1/aggregate-results').json()
pprint(r)

data = pd.read_csv('https://raw.githubusercontent.com/x-atlas-consortia/hra-pop/refs/heads/main/output-data/v1.0/reports/atlas/donor-info.csv')
pprint(data)
