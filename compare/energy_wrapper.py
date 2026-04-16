"""
energy_wrapper.py
Wraps the STONNE energy calculation script.

STONNE command from docs:
    ./calculate_energy.py -table_file=<energy_model.txt> \
                          -counter_file=<counters_file> \
                         [-out_file=<output_file>]

This wrapper:
- locates energy_tables/calculate_energy.py and energy_model.txt
- runs the script for a given counters file
- saves the raw output as energy.txt in the run folder
- tries to extract a single numeric energy value
- returns None on failure so the aggregator keeps going
"""

import os
import re
import subprocess
import sys


DEFAULT_ENERGY_SCRIPT = "stonne/energy_tables/calculate_energy.py"
DEFAULT_ENERGY_TABLE  = "stonne/energy_tables/energy_model.txt"


def _find_energy_assets(stonne_root: str = ".") -> tuple:
    """Locate the energy script and energy model file relative to stonne_root."""
    script = os.path.join(stonne_root, DEFAULT_ENERGY_SCRIPT)
    table  = os.path.join(stonne_root, DEFAULT_ENERGY_TABLE)
    return script, table


def _parse_energy(raw_text: str):
    """
    Try to extract a single numeric energy value from the script output.
    Strategy: find the last number in the text.
    Return None if nothing numeric is found.
    """
    numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", raw_text)
    if not numbers:
        return None
    try:
        return float(numbers[-1])
    except ValueError:
        return None


def run_energy(counters_file: str, run_output_dir: str, stonne_root: str = ".") -> dict:
    """
    Run the STONNE energy script for one run's counters file.

    Args:
        counters_file : path to the .counters file for this run
        run_output_dir: folder where energy.txt will be written
        stonne_root   : path to the stonne project root (defaults to cwd)

    Returns:
        dict with keys:
            success      : bool
            energy       : float or None
            energy_file  : path to saved energy.txt or None
            error        : error message string or None
    """
    result = {"success": False, "energy": None, "energy_file": None, "error": None}

    if not counters_file or not os.path.isfile(counters_file):
        result["error"] = f"counters file not found: {counters_file}"
        return result

    script, table = _find_energy_assets(stonne_root)
    if not os.path.isfile(script):
        result["error"] = f"energy script not found: {script}"
        return result
    if not os.path.isfile(table):
        result["error"] = f"energy model not found: {table}"
        return result

    os.makedirs(run_output_dir, exist_ok=True)
    energy_file = os.path.join(run_output_dir, "energy.txt")

    cmd = [
        "python3", script,
        f"-table_file={table}",
        f"-counter_file={counters_file}",
        f"-out_file={energy_file}",
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as e:
        result["error"] = f"failed to launch energy script: {e}"
        return result

    if proc.returncode != 0:
        result["error"] = f"energy script exited {proc.returncode}: {proc.stderr.strip()}"
        return result

    # Prefer the out_file if it was written; otherwise use stdout
    raw = ""
    if os.path.isfile(energy_file):
        with open(energy_file, "r") as f:
            raw = f.read()
    else:
        raw = proc.stdout
        with open(energy_file, "w") as f:
            f.write(raw)

    result["success"]     = True
    result["energy_file"] = energy_file
    result["energy"]      = _parse_energy(raw)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 compare/energy_wrapper.py <counters_file> <run_output_dir> [stonne_root]")
        sys.exit(1)

    counters = sys.argv[1]
    out_dir  = sys.argv[2]
    root     = sys.argv[3] if len(sys.argv) > 3 else "."

    r = run_energy(counters, out_dir, root)
    if r["success"]:
        print(f"Energy script ran successfully")
        print(f"  raw output   : {r['energy_file']}")
        print(f"  parsed energy: {r['energy']}")
    else:
        print(f"Energy calculation failed: {r['error']}")
        sys.exit(1)
