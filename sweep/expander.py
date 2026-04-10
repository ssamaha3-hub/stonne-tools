"""
expander.py
Computes the Cartesian product of all sweep parameters.
Returns a list of run specs the command builder and runner can use.
"""

from itertools import product


def _run_name_key(key: str) -> str:
    """Convert a param key to its run-name shorthand.
    e.g. T_M -> TM, T_N -> TN, T_K -> TK
    """
    return key.replace("_", "")


def expand(config: dict) -> list:
    """
    Expand a normalized config into a list of run specs.

    Each run spec contains:
        run_id      : zero-padded index string e.g. "run_0001"
        operation   : "DenseGEMM"
        params      : merged dict of fixed + this sweep combination
        run_name    : human-readable folder name e.g. "run_0001_TM1_TN1_TK32"
        output_dir  : full path to the run output folder

    Args:
        config: normalized dict from config_parser.load_config()

    Returns:
        list of run spec dicts, one per Cartesian product combination
    """
    fixed      = config["fixed"]
    sweep      = config["sweep"]
    output_root = config["global"]["output_root"]
    operation  = config["global"]["operation"]

    sweep_keys   = list(sweep.keys())
    sweep_values = [sweep[k] for k in sweep_keys]

    runs = []
    for i, combo in enumerate(product(*sweep_values), start=1):
        sweep_combo = dict(zip(sweep_keys, combo))

        # Merge fixed params with this sweep combination
        params = {**fixed, **sweep_combo}

        # Build run name from sweep values only (matches scanner format)
        sweep_parts = [
            f"{_run_name_key(k)}{v}" for k, v in sweep_combo.items()
        ]
        run_id   = f"run_{i:04d}"
        run_name = "_".join([run_id] + sweep_parts)

        runs.append({
            "run_id":     run_id,
            "operation":  operation,
            "params":     params,
            "run_name":   run_name,
            "output_dir": f"{output_root}/{run_name}",
        })

    return runs


if __name__ == "__main__":
    import sys
    try:
        from .config_parser import load_config
    except ImportError:
        from config_parser import load_config  # type: ignore[no-redef]

    if len(sys.argv) < 2:
        print("Usage: python -m sweep.expander <path_to_config.yaml>")
        sys.exit(1)

    config = load_config(sys.argv[1])
    runs   = expand(config)

    print(f"Total runs: {len(runs)}\n")
    for run in runs:
        print(f"  {run['run_name']}")
        print(f"    params     : {run['params']}")
        print(f"    output_dir : {run['output_dir']}")
        print()
