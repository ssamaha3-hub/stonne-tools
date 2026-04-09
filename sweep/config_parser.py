"""
config_parser.py
Reads YAML or JSON sweep config files.
Normalizes keys and types, splits into global/fixed/sweep sections,
and returns a clean dict the rest of the sweep runner can trust.
"""

import yaml
import json
import os
try:
    from .validator import validate_config
except ImportError:
    from validator import validate_config  # type: ignore[no-redef]

SUPPORTED_OPERATIONS = ["DenseGEMM", "FC", "SparseGEMM", "CONV"]

REQUIRED_TOP_LEVEL_KEYS = ["binary", "output_root", "operation", "fixed", "sweep"]

# These params are always integers
INT_PARAMS = {
    "M", "N", "K",
    "R", "S", "C", "G", "X", "Y", "strides",
    "num_ms", "dn_bw", "rn_bw",
    "T_M", "T_N", "T_K",
    "T_R", "T_S", "T_C", "T_G", "T_X_", "T_Y_",
    "print_stats",
}

# These params are always floats
FLOAT_PARAMS = {"MK_sparsity", "KN_sparsity"}



def _coerce_value(key: str, value):
    """Coerce a scalar value to the correct type for its parameter name."""
    if key in INT_PARAMS:
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValueError(
                f"Parameter '{key}' must be an integer, got: {value!r}"
            )
    if key in FLOAT_PARAMS:
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(
                f"Parameter '{key}' must be a number, got: {value!r}"
            )
    # Strings and unknown params: preserve exactly as-is
    return value


def _normalize_fixed(d: dict) -> dict:
    """Strip whitespace from keys and coerce values in a fixed-params dict."""
    if not isinstance(d, dict):
        raise ValueError("'fixed' must be a dictionary of parameter key-value pairs.")
    result = {}
    for k, v in d.items():
        key = k.strip()
        result[key] = _coerce_value(key, v)
    return result


def _normalize_sweep(d: dict) -> dict:
    """Strip whitespace from keys and coerce list values in a sweep dict."""
    if not isinstance(d, dict):
        raise ValueError("'sweep' must be a dictionary of parameter lists.")
    result = {}
    for k, v in d.items():
        key = k.strip()
        if not isinstance(v, list):
            raise ValueError(
                f"Sweep parameter '{key}' must be a list, got {type(v).__name__}."
            )
        if len(v) == 0:
            raise ValueError(f"Sweep parameter '{key}' cannot be an empty list.")
        result[key] = [_coerce_value(key, item) for item in v]
    return result


def load_config(config_path: str) -> dict:
    """
    Load and parse a sweep config YAML or JSON file.

    Returns a normalized config dict:
        {
            "global": {
                "binary": str,
                "output_root": str,
                "operation": str,
                "run_name_template": str  # optional
            },
            "fixed": { param: value, ... },
            "sweep": { param: [value, ...], ... }
        }

    Raises:
        FileNotFoundError: config file not found
        ValueError: structural or type errors in the config
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    _, ext = os.path.splitext(config_path.lower())
    with open(config_path, "r") as f:
        if ext == ".json":
            raw = json.load(f)
        else:
            # Default to YAML (.yaml, .yml, or unknown extension)
            raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError("Config file must be a YAML/JSON mapping at the top level.")

    # Normalize top-level keys
    raw = {k.strip(): v for k, v in raw.items()}

    # Check required top-level keys
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in raw:
            raise ValueError(f"Config is missing required top-level key: '{key}'")

    # Validate and extract operation
    operation = str(raw["operation"]).strip()
    if operation not in SUPPORTED_OPERATIONS:
        raise ValueError(
            f"Unsupported operation '{operation}'. "
            f"Supported operations: {SUPPORTED_OPERATIONS}"
        )

    # Merge base_dimensions into fixed if present (both formats are valid)
    if not isinstance(raw["fixed"], dict):
        raise ValueError("'fixed' must be a dictionary of parameter key-value pairs.")
    fixed_raw = dict(raw["fixed"])
    if "base_dimensions" in raw:
        if not isinstance(raw["base_dimensions"], dict):
            raise ValueError("'base_dimensions' must be a dictionary.")
        fixed_raw.update(raw["base_dimensions"])

    fixed = _normalize_fixed(fixed_raw)
    sweep = _normalize_sweep(raw["sweep"])

    # Build global settings
    global_settings = {
        "binary": str(raw["binary"]).strip(),
        "output_root": str(raw["output_root"]).strip(),
        "operation": operation,
    }
    if "run_name_template" in raw:
        global_settings["run_name_template"] = str(raw["run_name_template"]).strip()

    config = {
        "global": global_settings,
        "fixed": fixed,
        "sweep": sweep,
    }

    validate_config(config)

    return config


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_parser.py <path_to_config.yaml>")
        sys.exit(1)

    try:
        config = load_config(sys.argv[1])
        g = config["global"]
        print("Config loaded successfully!")
        print(f"  Operation : {g['operation']}")
        print(f"  Binary    : {g['binary']}")
        print(f"  Output    : {g['output_root']}")
        print(f"  Fixed     : {config['fixed']}")
        print(f"  Sweep     : {config['sweep']}")

        total = 1
        for values in config["sweep"].values():
            total *= len(values)
        print(f"  Total runs: {total}")

    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
