#!/usr/bin/env python3
import os
import platform
import subprocess
import sys
from pathlib import Path

# Project root (where setup_and_run.py lives)
ROOT = Path(__file__).parent
VENV = ROOT / ".venv"

# Step 1: create venv if it doesn’t exist
if not VENV.exists():
    print("🔧 Creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])

# Step 2: install dependencies
pip_path = VENV / ("Scripts" if platform.system() == "Windows" else "bin") / "pip"
print("📦 Installing dependencies...")
subprocess.check_call([str(pip_path), "install", "-r", str(ROOT / "requirements.txt")])

# Step 3: run scripts sequentially
python_path = VENV / ("Scripts" if platform.system() == "Windows" else "bin") / "python"

# Folder containing your scripts
SCRIPTS_DIR = ROOT / "scripts"

scripts = [
    "shared.py",
    "10-identify-cell-types-ftu-only.py",
    "20-hra-pop-preprocessing-cell-type-population.py",
    "30-hra-pop-preprocessing-metadata.py",
    "40-anatomogram-preprcossing-cell-type-population.py",
    "50-anatomogram-preprocessing-metadata.py",
    "60-combine-all.py",
]

for script in scripts:
    script_path = SCRIPTS_DIR / script
    print(f"\n🚀 Running {script_path.relative_to(ROOT)}...")
    subprocess.check_call([str(python_path), str(script_path)])

print("\n✅ All scripts completed successfully!")
