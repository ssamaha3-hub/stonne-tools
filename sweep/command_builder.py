"""
command_builder.py
Builds the STONNE CLI command array for a single run spec.

STONNE CLI syntax:
    ./stonne [-CONV | -FC | -SparseGEMM | -DenseGEMM] [hardware params] [dimension and tile params]

Example output:
    ["./stonne/stonne", "-DenseGEMM", "-M=20", "-N=20", "-K=256",
     "-num_ms=256", "-dn_bw=64", "-rn_bw=64", "-T_M=1", "-T_N=1", "-T_K=32"]
"""


def build_command(binary: str, run_spec: dict) -> list:
    """
    Build the STONNE CLI command for one run.

    Args:
        binary  : path to the stonne binary e.g. "./stonne/stonne"
        run_spec: a run spec dict from expander.expand()

    Returns:
        list of strings ready to pass to subprocess.run()
    """
    operation = run_spec["operation"]
    params    = run_spec["params"]

    cmd = [binary, f"-{operation}"]
    for key, value in params.items():
        cmd.append(f"-{key}={value}")

    return cmd


if __name__ == "__main__":
    import sys
    try:
        from .config_parser import load_config
        from .expander import expand
    except ImportError:
        from config_parser import load_config  # type: ignore[no-redef]
        from expander import expand             # type: ignore[no-redef]

    if len(sys.argv) < 2:
        print("Usage: python -m sweep.command_builder <path_to_config.yaml>")
        sys.exit(1)

    config = load_config(sys.argv[1])
    runs   = expand(config)

    print(f"Total commands: {len(runs)}\n")
    for run in runs:
        binary = config["global"]["binary"]
        cmd    = build_command(binary, run)
        print(f"  {run['run_name']}")
        print(f"    {' '.join(cmd)}")
        print()
