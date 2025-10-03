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

# Folder containing scripts
SCRIPTS_DIR = ROOT / "scripts"

scripts_to_run = sorted([
    file
    for file in os.listdir(SCRIPTS_DIR)
    if file.split(".")[-1] == "py" and file.split(".")[-2] != 'shared'
])

for script in scripts_to_run:
    script_path = SCRIPTS_DIR / script
    print(f"\n🚀 Running {script_path.relative_to(ROOT)}...")
    subprocess.check_call([str(python_path), str(script_path)])

print("\n✅ All scripts completed successfully!")
