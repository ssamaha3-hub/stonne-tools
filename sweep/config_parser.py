"""
config_parser.py
Reads and validates the sweep YAML config file.
Returns a clean dictionary the rest of the sweep runner can use.
"""

import yaml
import os


REQUIRED_TOP_LEVEL_KEYS = ["binary", "output_root", "operation", "fixed", "sweep"]
SUPPORTED_OPERATIONS = ["DenseGEMM"]
REQUIRED_FIXED_KEYS_DENSEGEMM = ["M", "N", "K", "num_ms", "dn_bw", "rn_bw"]
REQUIRED_SWEEP_KEYS_DENSEGEMM = ["T_M", "T_N", "T_K"]


def load_config(config_path: str) -> dict:
    """
    Load and validate a sweep config YAML file.

    Args:
        config_path: Path to the YAML config file.

    Returns:
        A validated config dictionary.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If the config is invalid or missing required fields.
    """

    # --- Check file exists ---
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # --- Load YAML ---
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("Config file must be a YAML mapping (dictionary).")

    # --- Check top level keys ---
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in config:
            raise ValueError(f"Config is missing required top-level key: '{key}'")

    # --- Validate operation ---
    operation = config["operation"]
    if operation not in SUPPORTED_OPERATIONS:
        raise ValueError(
            f"Unsupported operation '{operation}'. "
            f"Supported operations: {SUPPORTED_OPERATIONS}"
        )

    # --- Validate fixed params ---
    fixed = config["fixed"]
    if not isinstance(fixed, dict):
        raise ValueError("'fixed' must be a dictionary of parameter key-value pairs.")

    for key in REQUIRED_FIXED_KEYS_DENSEGEMM:
        if key not in fixed:
            raise ValueError(
                f"DenseGEMM requires fixed parameter '{key}' but it is missing."
            )

    # --- Validate sweep params ---
    sweep = config["sweep"]
    if not isinstance(sweep, dict):
        raise ValueError("'sweep' must be a dictionary of parameter lists.")

    for key in REQUIRED_SWEEP_KEYS_DENSEGEMM:
        if key not in sweep:
            raise ValueError(
                f"DenseGEMM requires sweep parameter '{key}' but it is missing."
            )

    for key, values in sweep.items():
        if not isinstance(values, list):
            raise ValueError(
                f"Sweep parameter '{key}' must be a list, got {type(values).__name__}."
            )
        if len(values) == 0:
            raise ValueError(
                f"Sweep parameter '{key}' cannot be an empty list."
            )

    # --- Validate binary path (warn if missing, don't hard fail) ---
    binary = config["binary"]
    if not os.path.exists(binary):
        print(f"[WARNING] Binary not found at '{binary}'. Make sure STONNE is built before running.")

    # --- Return clean normalized config ---
    return {
        "binary": binary,
        "output_root": config["output_root"],
        "operation": operation,
        "fixed": fixed,
        "sweep": sweep,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_parser.py <path_to_config.yaml>")
        sys.exit(1)

    config_path = sys.argv[1]

    try:
        config = load_config(config_path)
        print("Config loaded successfully!")
        print(f"  Operation : {config['operation']}")
        print(f"  Binary    : {config['binary']}")
        print(f"  Output    : {config['output_root']}")
        print(f"  Fixed     : {config['fixed']}")
        print(f"  Sweep     : {config['sweep']}")

        # Calculate total runs
        total = 1
        for values in config["sweep"].values():
            total *= len(values)
        print(f"  Total runs: {total}")

    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
