# stonne-tools

## What this solves

STONNE is a great simulator, but running many experiments and comparing them is a manual slog. One CLI command per run, timestamped files everywhere, energy computed by a separate script, and no way to see results side by side.

This repo fixes that with two small tools:

- `sweep/` reads a YAML config and runs every parameter combination automatically
- `compare/` collects the outputs, runs the energy calculator, and writes one CSV

The result: one command to run 12 experiments, one command to see them ranked.

Some parameter combinations in the sweep are intentionally invalid. STONNE enforces internal constraints on tile sizes, and when a configuration exceeds those limits the simulation aborts. Failed runs are captured and recorded in each run folder (`status.json`, `stderr.log`).

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
# Preview the config
python3 -m sweep.config_parser sweep/configs/densegemm_sweep.yaml

# Preview all expanded run specs
python3 -m sweep.expander sweep/configs/densegemm_sweep.yaml

# Preview the CLI commands that will be run
python3 -m sweep.command_builder sweep/configs/densegemm_sweep.yaml

# Run the full sweep
python3 -m sweep.runner sweep/configs/densegemm_sweep.yaml

# Scan results
python3 compare/scanner.py ./experiment_runs

# Generate summary CSV
python3 -m compare.main ./experiment_runs ./summary.csv .
```

---

## Contribution 1: Parameter Sweep Engine (`sweep/`)

Takes a YAML config file specifying fixed parameters and lists of values to sweep, then automatically executes every combination as a separate STONNE simulation.

- `config_parser.py` — loads and validates the YAML config
- `validator.py` — enforces hardware constraints (powers of 2, required params)
- `expander.py` — computes the Cartesian product of all sweep parameter lists
- `command_builder.py` — converts each run spec into a STONNE CLI command
- `runner.py` — executes all commands, captures output, writes `status.json` per run

### Example config (`sweep/configs/densegemm_sweep.yaml`)

```yaml
binary: ./stonne/stonne/stonne
output_root: ./experiment_runs
operation: DenseGEMM

fixed:
  M: 20
  N: 20
  K: 256
  num_ms: 256
  dn_bw: 64
  rn_bw: 64
  print_stats: 1

sweep:
  T_M: [1, 2, 4]
  T_N: [1, 2]
  T_K: [32, 64]
```

This produces 12 total runs (3 × 2 × 2).

---

## Contribution 2: Result Comparison Tool (`compare/`)

Reads all run output directories produced by the sweep engine and aggregates results into a single CSV.

- `scanner.py` — walks `experiment_runs/`, reads `status.json` per run
- `stats_parser.py` — extracts cycles, bandwidth, and hardware config from STONNE's stats output
- `energy_wrapper.py` — runs STONNE's energy calculator and parses the result
- `aggregator.py` — merges all metrics into one flat row per run
- `csv_export.py` / `main.py` — writes the final summary CSV

### Output columns

`run_name`, `status`, `TM`, `TN`, `TK`, `num_ms`, `dn_bw`, `rn_bw`, `cycles`, `layer_type`, `CB_WIRE_WRITE`, `CB_WIRE_READ`, `FIFO_PUSH`, `FIFO_POP`, `energy`, `stats_file`, `counters_file`, `energy_file`
