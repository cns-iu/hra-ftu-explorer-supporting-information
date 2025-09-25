#!/bin/bash
set -e  # stop if any script fails

echo "Running script1..."
python3 scripts/00-script.py

echo "Running script2..."
python3 scripts/01-script.py

echo "Running script3..."
python3 scripts/02-script.py

echo "Running script4..."
python3 scripts/03-script.py

echo "✅ All scripts finished successfully"