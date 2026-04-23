# keep stonne flags in a predictable order so commands are easier to read and diff
PREFERRED_ORDER = [
    "M",
    "N",
    "K",
    "num_ms",
    "dn_bw",
    "rn_bw",
    "print_stats",
    "T_M",
    "T_N",
    "T_K",
]


# build the final stonne command list for one run
def build_command(binary, run_spec):
    operation = run_spec["operation"]
    params = run_spec["params"]

    cmd = [binary, f"-{operation}"]
    seen = set()

    # add common parameters in a stable preferred order first
    for key in PREFERRED_ORDER:
        if key in params:
            cmd.append(f"-{key}={params[key]}")
            seen.add(key)

    # add any extra parameters not covered above
    for key in sorted(params.keys()):
        if key not in seen:
            cmd.append(f"-{key}={params[key]}")

    return cmd


if __name__ == "__main__":
    import sys
    try:
        from .config_parser import load_config
        from .expander import expand
    except ImportError:
        from config_parser import load_config
        from expander import expand

    if len(sys.argv) < 2:
        print("Usage: python -m sweep.command_builder <config.yaml>")
        sys.exit(1)

    config = load_config(sys.argv[1])
    runs = expand(config)

    print(f"Total commands: {len(runs)}\n")
    for run in runs:
        binary = config["global"]["binary"]
        cmd = build_command(binary, run)
        print(f"  {run['run_name']}")
        print(f"    {' '.join(cmd)}")
        print()