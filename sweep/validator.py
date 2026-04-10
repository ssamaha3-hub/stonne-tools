"""
validator.py
Validates a normalized config dict produced by config_parser.load_config().

Call validate_config(config) as the single entry point.
Raises ValueError with a specific message on the first validation failure.
"""

import os

SUPPORTED_OPERATIONS = ["DenseGEMM"]

# Hardware params that must be powers of 2
POWER_OF_2_PARAMS = {"num_ms", "dn_bw", "rn_bw"}

# DenseGEMM required params
DENSEGEMM_FIXED   = {"M", "N", "K", "num_ms", "dn_bw", "rn_bw"}
DENSEGEMM_TILES   = {"T_M", "T_N", "T_K"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_power_of_2(n: int) -> bool:
    return isinstance(n, int) and n > 0 and (n & (n - 1)) == 0


# ---------------------------------------------------------------------------
# Validation sections
# ---------------------------------------------------------------------------

def validate_global(global_settings: dict) -> None:
    """
    Check:
    - operation is supported
    - output_root is writable (created if absent)
    Note: binary existence is checked at run time by the runner, not here.
    """
    operation = global_settings["operation"]
    output_root = global_settings["output_root"]

    if operation not in SUPPORTED_OPERATIONS:
        raise ValueError(
            f"Unsupported operation '{operation}'. "
            f"Supported operations: {SUPPORTED_OPERATIONS}"
        )

    try:
        os.makedirs(output_root, exist_ok=True)
    except OSError as e:
        raise ValueError(f"Could not create output_root '{output_root}': {e}")

    if not os.access(output_root, os.W_OK):
        raise ValueError(f"output_root '{output_root}' exists but is not writable.")


def validate_hardware(fixed: dict) -> None:
    """
    Check:
    - num_ms, dn_bw, rn_bw are present and positive
    - all three are powers of 2
    """
    for param in ["num_ms", "dn_bw", "rn_bw"]:
        if param not in fixed:
            raise ValueError(
                f"Hardware parameter '{param}' is required in 'fixed' but is missing."
            )
        val = fixed[param]
        if not isinstance(val, int) or val <= 0:
            raise ValueError(
                f"Hardware parameter '{param}' must be a positive integer, got: {val!r}"
            )
        if not _is_power_of_2(val):
            raise ValueError(
                f"Hardware parameter '{param}' must be a power of 2, got: {val}. "
                f"Valid examples: 1, 2, 4, 8, 16, 32, 64, 128, 256, 512."
            )


def validate_operation(fixed: dict, sweep: dict) -> None:
    """
    Check DenseGEMM required params and domain constraints.
    """
    all_keys = set(fixed.keys()) | set(sweep.keys())

    # M, N, K must be in fixed
    for param in DENSEGEMM_FIXED:
        if param not in fixed:
            raise ValueError(
                f"DenseGEMM requires '{param}' in 'fixed' but it is missing."
            )

    # Tile params can be in fixed or sweep
    for param in DENSEGEMM_TILES:
        if param not in all_keys:
            raise ValueError(
                f"DenseGEMM requires '{param}' but it is missing from "
                "both 'fixed' and 'sweep'."
            )

    # M, N, K must be positive integers
    for dim in ("M", "N", "K"):
        val = fixed[dim]
        if not isinstance(val, int) or val <= 0:
            raise ValueError(
                f"DenseGEMM requires '{dim}' to be a positive integer, got: {val!r}"
            )


def validate_sweep(sweep: dict) -> None:
    """
    Check:
    - every sweep value is a non-empty list
    - total Cartesian product is non-zero
    """
    if not sweep:
        raise ValueError(
            "'sweep' section is empty. At least one parameter must be swept."
        )

    total = 1
    for key, values in sweep.items():
        if not isinstance(values, list):
            raise ValueError(
                f"Sweep parameter '{key}' must be a list, got {type(values).__name__}."
            )
        if len(values) == 0:
            raise ValueError(f"Sweep parameter '{key}' cannot be an empty list.")
        total *= len(values)

    if total == 0:
        raise ValueError(
            "Sweep Cartesian product is zero-sized. Check your sweep parameter lists."
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def validate_config(config: dict) -> None:
    """
    Run all validation checks on a config dict from config_parser.load_config().

    Validates in order:
        1. Global settings (operation, output_root)
        2. Hardware parameters (num_ms, dn_bw, rn_bw)
        3. DenseGEMM required params and constraints
        4. Sweep structure and Cartesian product

    Raises ValueError with a specific message on the first failure.
    """
    global_settings = config["global"]
    fixed = config["fixed"]
    sweep = config["sweep"]

    validate_global(global_settings)
    validate_hardware(fixed)
    validate_operation(fixed, sweep)
    validate_sweep(sweep)


if __name__ == "__main__":
    import sys
    try:
        from .config_parser import load_config
    except ImportError:
        from config_parser import load_config  # type: ignore[no-redef]

    if len(sys.argv) < 2:
        print("Usage: python -m sweep.validator <path_to_config.yaml>")
        sys.exit(1)

    try:
        config = load_config(sys.argv[1])
        validate_config(config)
        print("Validation passed.")
    except (FileNotFoundError, ValueError) as e:
        print(f"[VALIDATION ERROR] {e}")
        sys.exit(1)
