import os
import sys


def scan_runs(root_dir):
    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir} is not a directory")
        return []

    records = []

    for entry in sorted(os.listdir(root_dir)):
        run_path = os.path.join(root_dir, entry)
        if not os.path.isdir(run_path):
            continue

        record = {
            "run_name": entry,
            "run_path": run_path,
            "stats_file": None,
            "counters_file": None,
            "params": {},
        }

        for filename in os.listdir(run_path):
            filepath = os.path.join(run_path, filename)
            if filename.endswith(".txt"):
                record["stats_file"] = filepath
            elif filename.endswith(".counters"):
                record["counters_file"] = filepath

        record["params"] = parse_run_name(entry)
        records.append(record)

    return records


def parse_run_name(run_name):
    params = {}
    parts = run_name.split("_")
    i = 0
    while i < len(parts):
        part = parts[i]
        for key in ["TM", "TN", "TK"]:
            if part.startswith(key) and part[len(key):].isdigit():
                params[key] = int(part[len(key):])
        i += 1
    return params


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "./experiment_runs"
    runs = scan_runs(root)
    print(f"Found {len(runs)} run(s) in {root}\n")
    for r in runs:
        print(f"  Run     : {r['run_name']}")
        print(f"  Params  : {r['params']}")
        print(f"  Stats   : {r['stats_file']}")
        print(f"  Counters: {r['counters_file']}")
        print()
