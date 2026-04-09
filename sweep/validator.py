"""
validator.py
Validates a normalized config dict produced by config_parser.load_config().

Call validate_config(config) as the single entry point.
Raises ValueError with a specific message on the first validation failure.
"""

import os

SUPPORTED_OPERATIONS = ["DenseGEMM", "FC", "SparseGEMM", "CONV"]

# Hardware params that must be powers of 2
POWER_OF_2_PARAMS = {"num_ms", "dn_bw", "rn_bw"}

# Valid sparse dataflow strings as defined in STONNE docs
SUPPORTED_DATAFLOWS = ["MK_STA_KN_STR", "KN_STA_MK_STR", "MK_STA_MK_STR"]

# Required params per operation.
# "fixed_only"     -> must appear in fixed (not sweep)
# "fixed_or_sweep" -> can appear in either fixed or sweep
OPERATION_REQUIREMENTS = {
    "DenseGEMM": {
        "fixed_only":     {"M", "N", "K", "num_ms", "dn_bw", "rn_bw"},
        "fixed_or_sweep": {"T_M", "T_N", "T_K"},
    },
    "FC": {
        "fixed_only":     {"M", "N", "K", "num_ms", "dn_bw", "rn_bw"},
        "fixed_or_sweep": {"T_M", "T_N", "T_K"},
    },
    "SparseGEMM": {
        "fixed_only":     {"M", "N", "K", "MK_sparsity", "KN_sparsity", "num_ms", "dn_bw", "rn_bw"},
        "fixed_or_sweep": set(),
    },
    "CONV": {
        "fixed_only":     {"R", "S", "C", "K", "G", "N", "X", "Y", "strides", "num_ms", "dn_bw", "rn_bw"},
        "fixed_or_sweep": {"T_R", "T_S", "T_C", "T_K", "T_G", "T_N", "T_X_", "T_Y_"},
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_power_of_2(n: int) -> bool:
    return isinstance(n, int) and n > 0 and (n & (n - 1)) == 0


def _all_keys(fixed: dict, sweep: dict) -> set:
    return set(fixed.keys()) | set(sweep.keys())


# ---------------------------------------------------------------------------
# Validation sections
# ---------------------------------------------------------------------------

def validate_global(global_settings: dict) -> None:
    """
    Check:
    - operation is supported
    - output_root is writable (created if absent)
    Note: binary existence is checked at run time, not here.
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


def validate_operation(fixed: dict, sweep: dict, operation: str) -> None:
    """
    Check operation-specific required params and domain constraints.
    """
    reqs = OPERATION_REQUIREMENTS[operation]
    all_keys = _all_keys(fixed, sweep)

    # Params that must be in fixed (not sweep)
    for param in reqs["fixed_only"]:
        if param not in fixed:
            raise ValueError(
                f"{operation} requires '{param}' in 'fixed' but it is missing."
            )

    # Params that can be in either fixed or sweep
    for param in reqs["fixed_or_sweep"]:
        if param not in all_keys:
            raise ValueError(
                f"{operation} requires '{param}' but it is missing from "
                "both 'fixed' and 'sweep'."
            )

    # Operation-specific domain checks
    if operation in ("DenseGEMM", "FC"):
        _validate_dense(fixed, operation)
    elif operation == "SparseGEMM":
        _validate_sparsegemm(fixed)
    elif operation == "CONV":
        _validate_conv(fixed, sweep)


def _validate_dense(fixed: dict, operation: str) -> None:
    for dim in ("M", "N", "K"):
        val = fixed[dim]
        if not isinstance(val, int) or val <= 0:
            raise ValueError(
                f"{operation} requires '{dim}' to be a positive integer, got: {val!r}"
            )


def _validate_sparsegemm(fixed: dict) -> None:
    for dim in ("M", "N", "K"):
        val = fixed[dim]
        if not isinstance(val, int) or val <= 0:
            raise ValueError(
                f"SparseGEMM requires '{dim}' to be a positive integer, got: {val!r}"
            )

    for sparsity_key in ("MK_sparsity", "KN_sparsity"):
        val = fixed[sparsity_key]
        try:
            val = float(val)
        except (ValueError, TypeError):
            raise ValueError(
                f"SparseGEMM '{sparsity_key}' must be a number between 0 and 100."
            )
        if not (0.0 <= val <= 100.0):
            raise ValueError(
                f"SparseGEMM '{sparsity_key}' must be between 0 and 100, got: {val}"
            )

    if "dataflow" in fixed:
        dataflow = fixed["dataflow"]
        if dataflow not in SUPPORTED_DATAFLOWS:
            raise ValueError(
                f"SparseGEMM dataflow '{dataflow}' is not recognized. "
                f"Supported dataflows: {SUPPORTED_DATAFLOWS}"
            )


def _validate_conv(fixed: dict, sweep: dict) -> None:  # noqa: ARG001
    for dim in ("R", "S", "C", "K", "G", "N", "X", "Y", "strides"):
        val = fixed[dim]
        if not isinstance(val, int) or val <= 0:
            raise ValueError(
                f"CONV requires '{dim}' to be a positive integer, got: {val!r}"
            )

    # Tile divisibility constraints (only when tile is in fixed, not sweep)
    # Constraint: dimension must be divisible by its tile value
    tile_dim_pairs = [
        ("T_R", "R"),
        ("T_S", "S"),
        ("T_C", "C"),
    ]
    for tile_key, dim_key in tile_dim_pairs:
        if tile_key in fixed:
            tile_val = fixed[tile_key]
            dim_val = fixed[dim_key]
            if dim_val % tile_val != 0:
                raise ValueError(
                    f"CONV tile constraint violated: {dim_key} ({dim_val}) must be "
                    f"divisible by {tile_key} ({tile_val}). "
                    f"Got {dim_val} % {tile_val} = {dim_val % tile_val}."
                )


def validate_sweep(sweep: dict) -> None:
    """
    Check:
    - every sweep value is a list
    - no list is empty
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
        1. Global settings (binary, operation, output_root)
        2. Hardware parameters (num_ms, dn_bw, rn_bw)
        3. Operation-specific parameters and constraints
        4. Sweep structure and Cartesian product

    Raises ValueError with a specific message on the first failure.
    """
    global_settings = config["global"]
    fixed = config["fixed"]
    sweep = config["sweep"]
    operation = global_settings["operation"]

    validate_global(global_settings)
    validate_hardware(fixed)
    validate_operation(fixed, sweep, operation)
    validate_sweep(sweep)


if __name__ == "__main__":
    import sys
    from config_parser import load_config

    if len(sys.argv) < 2:
        print("Usage: python validator.py <path_to_config.yaml>")
        sys.exit(1)

    try:
        config = load_config(sys.argv[1])
        validate_config(config)
        print("Validation passed.")
    except (FileNotFoundError, ValueError) as e:
        print(f"[VALIDATION ERROR] {e}")
        sys.exit(1)
