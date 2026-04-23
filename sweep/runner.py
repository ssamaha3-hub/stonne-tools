import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from .config_parser import load_config
    from .expander import expand
    from .command_builder import build_command
except ImportError:
    from config_parser import load_config
    from expander import expand
    from command_builder import build_command


# generate a readable timestamp for run metadata
def _timestamp():
    return datetime.now().isoformat(timespec="seconds")


# create the run output directory if it does not exist
def _ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


# helper to write plain text files
def _write_text(path, content):
    with open(path, "w") as f:
        f.write(content)


# helper to write json files
def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# detect files created by STONNE inside one run folder
def _detect_output_files(output_dir):
    stats_file = None
    counters_file = None
    all_files = []

    # files created by our runner, not by STONNE itself
    runner_files = {"run_config.json", "status.json", "command.txt", "stdout.log", "stderr.log"}

    for entry in sorted(os.listdir(output_dir)):
        full_path = os.path.join(output_dir, entry)

        if not os.path.isfile(full_path):
            continue

        all_files.append(entry)

        # skip files created by the runner
        if entry in runner_files:
            continue

        # stats file is a .txt output file
        if entry.endswith(".txt") and stats_file is None:
            stats_file = full_path

        # counters file contains "counter" in the name
        if "counter" in entry.lower() and counters_file is None:
            counters_file = full_path

    return {
        "stats_file": stats_file,
        "counters_file": counters_file,
        "all_files": all_files,
    }


# execute one stonne run and save all related output files
def run_one(binary, run_spec):
    output_dir = run_spec["output_dir"]
    _ensure_dir(output_dir)

    # build the stonne command
    cmd = build_command(binary, run_spec)

    # save the run config and command for reproducibility
    _write_json(os.path.join(output_dir, "run_config.json"), run_spec)
    _write_text(os.path.join(output_dir, "command.txt"), " ".join(cmd) + "\n")

    # set output_dir so stonne writes its outputs into this run folder
    env = os.environ.copy()
    env["OUTPUT_DIR"] = output_dir

    started_at = _timestamp()

    try:
        # run the stonne process and capture stdout/stderr
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)

        _write_text(os.path.join(output_dir, "stdout.log"), result.stdout)
        _write_text(os.path.join(output_dir, "stderr.log"), result.stderr)

        # detect generated stats and counters files after the run
        detected = _detect_output_files(output_dir)
        success = result.returncode == 0

        status = {
            "run_id": run_spec["run_id"],
            "run_name": run_spec["run_name"],
            "operation": run_spec["operation"],
            "params": run_spec["params"],
            "command": cmd,
            "return_code": result.returncode,
            "success": success,
            "started_at": started_at,
            "finished_at": _timestamp(),
            "output_dir": output_dir,
            # keep the existing key name used elsewhere in the analyzer
            "stats_json": detected["stats_file"],
            "counters_file": detected["counters_file"],
            "all_files": detected["all_files"],
        }

    except FileNotFoundError as e:
        # if the binary is missing, still write logs and status so the failure is recorded
        _write_text(os.path.join(output_dir, "stdout.log"), "")
        _write_text(os.path.join(output_dir, "stderr.log"), str(e) + "\n")

        status = {
            "run_id": run_spec["run_id"],
            "run_name": run_spec["run_name"],
            "operation": run_spec["operation"],
            "params": run_spec["params"],
            "command": cmd,
            "return_code": None,
            "success": False,
            "started_at": started_at,
            "finished_at": _timestamp(),
            "output_dir": output_dir,
            "stats_json": None,
            "counters_file": None,
            "all_files": [],
            "error": f"Binary not found: {e}",
        }

    # write the final status.json used later by the analyzer
    _write_json(os.path.join(output_dir, "status.json"), status)
    return status


# run the full sweep defined by the config file
def run_all(config):
    binary = config["global"]["binary"]
    runs = expand(config)
    statuses = []

    for run_spec in runs:
        print(f"Running {run_spec['run_name']} ...")
        status = run_one(binary, run_spec)
        statuses.append(status)

        if status["success"]:
            print(f"  done: return_code={status['return_code']}")
        else:
            print(f"  failed: return_code={status['return_code']}")

    return statuses


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m sweep.runner <config.yaml>")
        sys.exit(1)

    try:
        config = load_config(sys.argv[1])
        results = run_all(config)

        total = len(results)
        passed = sum(1 for r in results if r["success"])

        print("\nRun summary")
        print(f"  total  : {total}")
        print(f"  passed : {passed}")
        print(f"  failed : {total - passed}")

    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)