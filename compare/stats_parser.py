import json
import os
import sys


def parse_stats(stats_file):
    if not stats_file or not os.path.isfile(stats_file):
        return None

    try:
        with open(stats_file, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

    metrics = {}

    metrics["cycles"] = data.get("GlobalStats", {}).get("N_cycles", None)

    sdmem = data.get("hardwareConfiguration", {}).get("SDMemory", {})
    metrics["dn_bw"] = sdmem.get("dn_bw", None)
    metrics["rn_bw"] = sdmem.get("rn_bw", None)

    ms_net = data.get("hardwareConfiguration", {}).get("MSNetwork", {})
    metrics["num_ms"] = ms_net.get("ms_size", None)

    layer = data.get("LayerConfiguration", {})
    metrics["layer_type"] = layer.get("Layer_Type", None)

    return metrics


def parse_counters(counters_file):
    if not counters_file or not os.path.isfile(counters_file):
        return None

    totals = {
        "CB_WIRE_WRITE": 0,
        "CB_WIRE_READ": 0,
        "FIFO_PUSH": 0,
        "FIFO_POP": 0,
    }

    try:
        with open(counters_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("CB_WIRE"):
                    parts = line.split()
                    for part in parts:
                        if part.startswith("WRITE="):
                            totals["CB_WIRE_WRITE"] += int(part.split("=")[1])
                        elif part.startswith("READ="):
                            totals["CB_WIRE_READ"] += int(part.split("=")[1])
                elif line.startswith("FIFO"):
                    parts = line.split()
                    for part in parts:
                        if part.startswith("PUSH="):
                            totals["FIFO_PUSH"] += int(part.split("=")[1])
                        elif part.startswith("POP="):
                            totals["FIFO_POP"] += int(part.split("=")[1])
    except IOError:
        return None

    return totals


if __name__ == "__main__":
    stats_path = sys.argv[1] if len(sys.argv) > 1 else None
    counters_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not stats_path:
        print("Usage: python3 stats_parser.py <stats.txt> [counters.counters]")
        sys.exit(1)

    metrics = parse_stats(stats_path)
    counters = parse_counters(counters_path)

    print("Stats:")
    if metrics:
        for k, v in metrics.items():
            print(f"  {k}: {v}")
    else:
        print("  Could not parse stats file")

    print("\nCounters:")
    if counters:
        for k, v in counters.items():
            print(f"  {k}: {v}")
    else:
        print("  No counters file or could not parse")