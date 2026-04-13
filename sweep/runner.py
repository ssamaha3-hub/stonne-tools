"""
runner.py
Executes expanded STONNE runs and stores outputs per run.
"""

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
    from config_parser import load_config  # type: ignore[no-redef]
    from expander import expand  # type: ignore[no-redef]
    from command_builder import build_command  # type: ignore[no-redef]


def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _write_text(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


def _write_json(path: str, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _detect_output_files(output_dir: str) -> dict:
    """
    Best-effort detection of files produced by STONNE.

    Returns:
        {
            "stats_json": "<path or None>",
            "counters_file": "<path or None>",
            "all_files": [ ... ]
        }
    """
    stats_json = None
    counters_file = None
    all_files = []

    for entry in sorted(os.listdir(output_dir)):
        full_path = os.path.join(output_dir, entry)
        if not os.path.isfile(full_path):
            continue

        all_files.append(entry)

        # Ignore files created by our runner
        if entry in {
            "run_config.json",
            "status.json",
            "command.txt",
            "stdout.log",
            "stderr.log",
        }:
            continue

        # detect stats file (STONNE outputs .txt, not JSON)
        if entry.endswith(".txt") and stats_json is None:
            stats_json = full_path

        # Loose match for counters file
        lowered = entry.lower()
        if "counter" in lowered and counters_file is None:
            counters_file = full_path

    return {
        "stats_file": stats_json,
        "counters_file": counters_file,
        "all_files": all_files,
    }


def run_one(binary: str, run_spec: dict) -> dict:
    """
    Execute a single run spec.

    Returns:
        status dict for status.json
    """
    output_dir = run_spec["output_dir"]
    _ensure_dir(output_dir)

    cmd = build_command(binary, run_spec)
    cmd_text = " ".join(cmd)

    run_config_path = os.path.join(output_dir, "run_config.json")
    command_path = os.path.join(output_dir, "command.txt")
    stdout_path = os.path.join(output_dir, "stdout.log")
    stderr_path = os.path.join(output_dir, "stderr.log")
    status_path = os.path.join(output_dir, "status.json")

    _write_json(run_config_path, run_spec)
    _write_text(command_path, cmd_text + "\n")

    env = os.environ.copy()
    env["OUTPUT_DIR"] = output_dir

    started_at = _timestamp()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        _write_text(stdout_path, result.stdout)
        _write_text(stderr_path, result.stderr)

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
            "stats_json": detected["stats_json"],
            "counters_file": detected["counters_file"],
            "all_files": detected["all_files"],
        }

    except FileNotFoundError as e:
        _write_text(stdout_path, "")
        _write_text(stderr_path, str(e) + "\n")

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

    _write_json(status_path, status)
    return status


def run_all(config: dict) -> list:
    """
    Expand and execute all runs in the config.
    """
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
        print("Usage: python -m sweep_runner.runner <path_to_config.yaml>")
        sys.exit(1)

    try:
        config = load_config(sys.argv[1])
        results = run_all(config)

        total = len(results)
        passed = sum(1 for r in results if r["success"])
        failed = total - passed

        # Some runs may fail due to STONNE constraints on tile sizes.
        print("\nRun summary")
        print(f"  total  : {total}")
        print(f"  passed : {passed}")
        print(f"  failed : {failed}")

    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
