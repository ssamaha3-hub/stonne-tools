"""
aggregator.py
Merges per-run metadata, stats, counters, and energy into one flat row per run.

Input:
- scanner record (run_name, run_path, stats_file, counters_file, params)
- stats_parser output (cycles, num_ms, dn_bw, rn_bw, layer_type)
- counters_parser output (CB_WIRE_WRITE, CB_WIRE_READ, FIFO_PUSH, FIFO_POP)
- energy_wrapper output (energy float or None)

Output:
- one flat dict per run, ready to be written as a CSV row
"""

import os
import sys


# Stable column order for summary rows
COLUMN_ORDER = [
    # run metadata
    "run_name",
    "status",
    # sweep params (parsed from run name by scanner)
    "TM", "TN", "TK",
    # hardware / stats
    "num_ms", "dn_bw", "rn_bw",
    "cycles", "layer_type",
    # counters totals
    "CB_WIRE_WRITE", "CB_WIRE_READ",
    "FIFO_PUSH", "FIFO_POP",
    # energy
    "energy",
    # file refs
    "stats_file", "counters_file", "energy_file",
]


def aggregate_run(record: dict, stats: dict, counters: dict, energy: dict) -> dict:
    """
    Build one flat row for a single run.

    Args:
        record  : scanner record for this run
        stats   : dict from stats_parser.parse_stats() or None
        counters: dict from stats_parser.parse_counters() or None
        energy  : dict from energy_wrapper.run_energy() or None

    Returns:
        flat dict with every column in COLUMN_ORDER (missing values are None)
    """
    row = {col: None for col in COLUMN_ORDER}

    row["run_name"] = record.get("run_name")
    params = record.get("params") or {}
    for key in ("TM", "TN", "TK"):
        row[key] = params.get(key)

    if stats:
        for key in ("cycles", "num_ms", "dn_bw", "rn_bw", "layer_type"):
            if key in stats:
                row[key] = stats[key]

    if counters:
        for key in ("CB_WIRE_WRITE", "CB_WIRE_READ", "FIFO_PUSH", "FIFO_POP"):
            if key in counters:
                row[key] = counters[key]

    if energy:
        row["energy"]      = energy.get("energy")
        row["energy_file"] = energy.get("energy_file")
        row["status"] = "success" if energy.get("success") else "energy_failed"
    else:
        row["status"] = "success" if stats else "no_stats"

    row["stats_file"]    = record.get("stats_file")
    row["counters_file"] = record.get("counters_file")

    return row


def aggregate_all(records: list, stonne_root: str = ".") -> list:
    """
    Run stats parsing, counters parsing, and energy calculation across all
    scanner records. Returns a list of flat rows ready for CSV export.

    Args:
        records    : list of scanner records from scanner.scan_runs()
        stonne_root: path to the stonne project root (for energy assets)
    """
    try:
        from .stats_parser import parse_stats, parse_counters
        from .energy_wrapper import run_energy
    except ImportError:
        from stats_parser import parse_stats, parse_counters  # type: ignore[no-redef]
        from energy_wrapper import run_energy                 # type: ignore[no-redef]

    rows = []
    for record in records:
        stats    = parse_stats(record.get("stats_file"))
        counters = parse_counters(record.get("counters_file"))
        energy   = None
        counters_file = record.get("counters_file")
        if counters_file and os.path.isfile(counters_file):
            energy = run_energy(counters_file, record["run_path"], stonne_root)

        rows.append(aggregate_run(record, stats, counters, energy))

    return rows


if __name__ == "__main__":
    try:
        from .scanner import scan_runs
    except ImportError:
        from scanner import scan_runs  # type: ignore[no-redef]

    root = sys.argv[1] if len(sys.argv) > 1 else "./experiment_runs"
    stonne_root = sys.argv[2] if len(sys.argv) > 2 else "."

    records = scan_runs(root)
    rows = aggregate_all(records, stonne_root)

    print(f"Aggregated {len(rows)} run(s) from {root}\n")
    for row in rows:
        print(f"  {row['run_name']}  ({row['status']})")
        for col in COLUMN_ORDER:
            if row[col] is not None and col not in ("stats_file", "counters_file", "energy_file", "run_name", "status"):
                print(f"    {col}: {row[col]}")
        print()
