# stonne-tools

Parameter sweep engine and result comparison tool for the STONNE neural network accelerator simulator.

STONNE runs one simulation at a time through its CLI. These tools add a sweep engine on top to run many simulations automatically, and a comparison tool to aggregate the results into one CSV.

**Known Behavior:** Some parameter combinations in the sweep are intentionally invalid. STONNE enforces internal constraints on tile sizes and hardware capacity. When a configuration exceeds these limits, the simulation aborts. Our tool captures these failures and records them in each run folder (`status.json`, `stderr.log`) for analysis.

---

## Setup

Clone the repo with submodules:

```bash
git clone --recurse-submodules https://github.com/ssamaha3-hub/stonne-tools.git
cd stonne-tools
```

Build STONNE (Linux/WSL only):

```bash
cd stonne/stonne
make
```

Install Python dependencies:

```bash
pip install pyyaml
```

---

## Running the Full Pipeline

```bash
# 1. Preview the config
python3 -m sweep.config_parser sweep/configs/densegemm_sweep.yaml

# 2. Preview expanded run specs
python3 -m sweep.expander sweep/configs/densegemm_sweep.yaml

# 3. Preview built CLI commands
python3 -m sweep.command_builder sweep/configs/densegemm_sweep.yaml

# 4. Run the full sweep
python3 -m sweep.runner sweep/configs/densegemm_sweep.yaml

# 5. Scan results
python3 compare/scanner.py ./experiment_runs

# 6. Generate summary CSV
python3 -m compare.main ./experiment_runs ./summary.csv .
```

Output: `summary.csv` with one row per run containing cycle counts, wire/FIFO counters, energy estimates, and status for all 12 configurations.

---

## Contribution 1: Parameter Sweep Engine

### Section 1 - Samer

Config format and parser.

`sweep/configs/densegemm_sweep.yaml` defines the sweep — which parameters are fixed and which are swept across multiple values. The example config sweeps `T_M`, `T_N`, and `T_K` producing 12 total runs.

`sweep/config_parser.py` loads the YAML config, normalizes keys and types, splits into fixed and sweep sections, and returns a clean dict the rest of the sweep engine can trust. Raises descriptive errors on missing or malformed fields.

`sweep/validator.py` enforces hardware constraints before any run begins. Checks that `num_ms`, `dn_bw`, and `rn_bw` are positive powers of two, that all required DenseGEMM parameters are present, and that the sweep Cartesian product is non-zero.

```bash
python3 -m sweep.config_parser sweep/configs/densegemm_sweep.yaml
```

Expected output:

```
Config loaded successfully!
  Operation : DenseGEMM
  Binary    : ./stonne/stonne/stonne
  Output    : ./experiment_runs
  Fixed     : {'M': 20, 'N': 20, 'K': 256, 'num_ms': 256, 'dn_bw': 64, 'rn_bw': 64, 'print_stats': 1}
  Sweep     : {'T_M': [1, 2, 4], 'T_N': [1, 2], 'T_K': [32, 64]}
  Total runs: 12
```

### Section 2 - Kobby

Expander and command builder.

`sweep/expander.py` takes the parsed config and computes the Cartesian product of all sweep parameter lists. For each combination it merges the fixed and sweep params into one flat dict and assigns a run ID, a human-readable run name, and an output directory path. The run names match the format the scanner expects — for example `run_0001_TM1_TN1_TK32`.

`sweep/command_builder.py` takes a run spec from the expander and builds the STONNE CLI command as a list of strings ready for `subprocess.run()`. For DenseGEMM it produces a command like `["./stonne/stonne/stonne", "-DenseGEMM", "-M=20", "-N=20", "-K=256", "-num_ms=256", "-dn_bw=64", "-rn_bw=64", "-T_M=1", "-T_N=1", "-T_K=32"]`.

```bash
python3 -m sweep.expander sweep/configs/densegemm_sweep.yaml
python3 -m sweep.command_builder sweep/configs/densegemm_sweep.yaml
```

Expected output:

```
Total runs: 12

  run_0001_TM1_TN1_TK32
    params     : {'M': 20, 'N': 20, 'K': 256, 'num_ms': 256, 'dn_bw': 64, 'rn_bw': 64, 'print_stats': 1, 'T_M': 1, 'T_N': 1, 'T_K': 32}
    output_dir : ./experiment_runs/run_0001_TM1_TN1_TK32
  ...

Total commands: 12

  run_0001_TM1_TN1_TK32
    ./stonne/stonne/stonne -DenseGEMM -M=20 -N=20 -K=256 -num_ms=256 -dn_bw=64 -rn_bw=64 -print_stats=1 -T_M=1 -T_N=1 -T_K=32
  ...
```

### Section 3 - Ify

Runner and CLI entry point.

`sweep/runner.py` iterates over all expanded run specs, executes each STONNE command via `subprocess.run()`, and captures stdout and stderr to log files in the run's output directory. After each run it scans the directory for STONNE output files and writes a `status.json` recording the run name, parameters, return code, success flag, timestamps, and paths to the stats and counters files. Runs that fail due to hardware constraint violations are logged and skipped without halting the sweep.

```bash
python3 -m sweep.runner sweep/configs/densegemm_sweep.yaml
```

Expected output:

```
Running run_0001_TM1_TN1_TK32 ...
  done: return_code=0
Running run_0002_TM1_TN1_TK64 ...
  done: return_code=0
...
Running run_0008_TM2_TN2_TK64 ...
  failed: return_code=-6

Run summary
  total  : 12
  passed : 8
  failed : 4
```

---

## Contribution 2: Result Comparison Tool

### Section 1 - Samer

Scanner and stats parser.

`compare/scanner.py` walks the `experiment_runs/` directory, finds every run folder, and inventories the output files inside each one. Reads `status.json` for run metadata and falls back to directory scanning when absent, filtering strictly to files starting with `output_stats` to avoid picking up runner-generated files like `command.txt`.

`compare/stats_parser.py` takes the two output files STONNE produces per run — a `.txt` JSON stats file and a `.counters` file — and extracts the key metrics from each. From the stats file it pulls cycles, bandwidth settings, and number of multiply-switch units. From the counters file it aggregates total wire writes, wire reads, FIFO pushes, and FIFO pops across all components.

```bash
python3 compare/scanner.py ./experiment_runs
```

Expected output:

```
Found 12 run(s) in ./experiment_runs

  Run        : run_0001_TM1_TN1_TK32
  Success    : True
  ReturnCode : 0
  Params     : {'M': 20, 'N': 20, 'K': 256, 'num_ms': 256, 'dn_bw': 64, 'rn_bw': 64, 'print_stats': 1, 'T_M': 1, 'T_N': 1, 'T_K': 32}
  Stats      : ./experiment_runs/run_0001_TM1_TN1_TK32/output_stats_...txt
  Counters   : ./experiment_runs/run_0001_TM1_TN1_TK32/output_stats_...counters
  ...
```

### Section 2 - Kobby

Energy wrapper and aggregator.

`compare/energy_wrapper.py` wraps STONNE's `calculate_energy.py` script. Given a counters file and a run output directory, it locates `stonne/stonne/energy_tables/calculate_energy.py` and `stonne/stonne/energy_tables/energy_model.txt`, runs the energy script, saves the raw output as `energy.txt` in the run folder, and parses a single numeric energy value from the result. If the energy script fails for any reason, it returns `None` instead of crashing so the aggregator can still produce rows for the other runs.

`compare/aggregator.py` takes a list of scanner records and produces one flat row per run for the CSV. Each row contains run metadata (name, status), sweep params (TM, TN, TK), hardware settings (num_ms, dn_bw, rn_bw), performance metrics (cycles, layer_type), counters totals (wire writes/reads, FIFO push/pop), the parsed energy value, and paths to the stats/counters/energy files. Column order is stable so the CSV export can consume it directly.

```bash
python3 compare/aggregator.py ./experiment_runs .
```

Expected output (abbreviated):

```
Aggregated 12 run(s) from ./experiment_runs

  run_0004_TM1_TN2_TK64  (success)
    TM: 1  TN: 2  TK: 64
    cycles: 5900
    energy: 28435.86
```

### Section 3 - Ify

CSV export and analyzer CLI.

`compare/csv_export.py` writes the aggregated rows to a CSV file using the stable column order from the aggregator.

`compare/main.py` is the CLI entry point tying the full pipeline together. It takes the experiment directory, output CSV path, and STONNE root as arguments and runs the full scanner → aggregator → CSV pipeline.

```bash
python3 -m compare.main ./experiment_runs ./summary.csv .
```

Expected output:

```
Wrote 12 row(s) to ./summary.csv
```

The CSV contains one row per run with columns: `run_name`, `status`, `TM`, `TN`, `TK`, `num_ms`, `dn_bw`, `rn_bw`, `cycles`, `layer_type`, `CB_WIRE_WRITE`, `CB_WIRE_READ`, `FIFO_PUSH`, `FIFO_POP`, `energy`, `stats_file`, `counters_file`, `energy_file`.
