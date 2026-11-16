#!/usr/bin/env python3
"""Set up the venv with scripts/00-setup_env.py, then run every other script in scripts/ in filename order."""
import platform
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent / "scripts"
SETUP_SCRIPT = SCRIPTS_DIR / "00-setup_env.py"
VENV_PYTHON = (
    SCRIPTS_DIR / ".venv" / ("Scripts" if platform.system() == "Windows" else "bin") / "python"
)

# Creates scripts/.venv (if needed) and installs scripts/requirements.txt
subprocess.check_call([sys.executable, str(SETUP_SCRIPT)])

scripts_to_run = sorted(
    script
    for script in SCRIPTS_DIR.glob("*.py")
    if script.name not in ("shared.py", SETUP_SCRIPT.name)
)

for script in scripts_to_run:
    print(f"\n--- Running: {script.name} ---", flush=True)
    # check_call stops here if a script fails, so later stages never read stale or missing outputs
    subprocess.check_call([str(VENV_PYTHON), str(script)], cwd=SCRIPTS_DIR)

print("\nAll scripts completed successfully!")
