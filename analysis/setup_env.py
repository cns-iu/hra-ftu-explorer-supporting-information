#!/usr/bin/env python3
"""Create a virtual environment for the analysis/ scripts and install requirements.txt.

Unlike data-preprocessor/set_up_and_run.py, this does NOT run any scripts —
analysis scripts are independent, run on demand (`python analysis/<script>.py`),
not a sequential pipeline.
"""
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"

if not VENV.exists():
    print("🔧 Creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])

pip_path = VENV / ("Scripts" if platform.system() == "Windows" else "bin") / "pip"
print("📦 Installing dependencies...")
subprocess.check_call([str(pip_path), "install", "-r", str(ROOT / "requirements.txt")])

activate_hint = (
    r".venv\Scripts\activate" if platform.system() == "Windows" else "source .venv/bin/activate"
)
print(f"\n✅ Environment ready. Activate it with: {activate_hint}")
