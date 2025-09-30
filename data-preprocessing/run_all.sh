#!/bin/bash
set -e  # stop if any script fails

pip install -r requirements.txt

echo "Running script 1..."
python3 scripts/10-identify-cell-types-ftu-only.py

echo "Running script 2..."
python3 scripts/20-hra-pop-preprocessing-cell-type-population.py

echo "Running script 3..."
python3 scripts/30-hra-pop-preprocessing-metadata.py

echo "Running script 4..."
python3 scripts/40-anatomogram-preprcossing-cell-type-population.py

echo "Running script 5..."
python3 scripts/50-anatomogram-preprocessing-metadata.py

echo "Running script 6..."
python3 scripts/60-combine-all.py

echo "✅ All scripts finished successfully"