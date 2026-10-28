#!/usr/bin/env python3
"""Create a virtual environment for the oral-cavity-data/ scripts and install requirements.txt.

This does NOT run any scripts — activate the venv and run them on demand.
"""
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"

if not VENV.exists():
    print("Creating virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])

python_path = VENV / ("Scripts" if platform.system() == "Windows" else "bin") / "python"
print("Installing dependencies...")
subprocess.check_call([str(python_path), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])

activate_hint = (
    r".venv\Scripts\activate" if platform.system() == "Windows" else "source .venv/bin/activate"
)
print(f"\nEnvironment ready. Activate it with: {activate_hint}")
