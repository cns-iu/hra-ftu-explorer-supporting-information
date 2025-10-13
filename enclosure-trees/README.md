# Supporting Information

Run the generate_hierarchy.py using by just changing the Organ Id and FTU is according to the Organ-
```
python -u "enclosure-trees\code\generate_hierarchy.py" --input "enclosure-trees\data\thymus.json" --organ-id "UBERON:0002370" --organ-label "thymus" --ftu-ids "UBERON:0002125" --output "enclosure-trees\output\hierarchy_organ_to_ct_new.json"

```

The result will be a hierarchical json file of Organs -> AS -> FTUs -> CTs

## Data

The ASCT tables data is stored in data folder organ wise.
In the output folder the hierarchical data is stored.

### The tree.html is a D3.js file where you can upload this hierarchical data to get tree visualization.