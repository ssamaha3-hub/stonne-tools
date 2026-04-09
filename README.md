# stonne-tools

Parameter sweep engine and result comparison tool for the STONNE neural network accelerator simulator.

STONNE runs one simulation at a time through its CLI. These tools add a sweep engine on top to run many simulations automatically, and a comparison tool to aggregate the results into one CSV.

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

## Contribution 1: Parameter Sweep Engine

### Section 1 - Samer

Config format and parser.

`sweep/configs/densegemm_sweep.yaml` defines the sweep — which parameters are fixed and which are swept across multiple values. The example config sweeps T_M, T_N, and T_K producing 18 total runs.

### Section 2 - Kobby

Config parser and validation rules.

`sweep/config_parser.py` reads that YAML or JSON, normalizes all keys and types, and splits the config into three sections: global settings (binary path, operation, output directory), fixed parameters, and sweep parameters. It supports all four STONNE operations — DenseGEMM, FC, SparseGEMM, and CONV. Integer parameters like M, N, K, and tile sizes are automatically coerced to int. Enum-style string arguments like `MK_STA_KN_STR` are preserved exactly. If a `base_dimensions` block is present it is merged into fixed automatically.

`sweep/validator.py` runs after parsing and checks that the config is actually runnable. It validates global settings (operation is supported, output directory is writable), hardware parameters (num_ms, dn_bw, rn_bw must be positive powers of 2), operation-specific required fields (e.g. DenseGEMM requires M, N, K, T_M, T_N, T_K), SparseGEMM sparsity ranges and dataflow string, CONV tile divisibility constraints (R % T_R = 0, S % T_S = 0, C % T_C = 0), and sweep structure (all values must be non-empty lists with a non-zero Cartesian product). Errors are specific — for example: `DenseGEMM requires 'T_K' but it is missing from both 'fixed' and 'sweep'.`

Run the parser and validator together:

```bash
python3 -m sweep.config_parser sweep/configs/densegemm_sweep.yaml
```

Expected output:

```
Config loaded successfully!
  Operation : DenseGEMM
  Binary    : ./stonne/stonne
  Output    : ./experiment_runs
  Fixed     : {'M': 20, 'N': 20, 'K': 256, 'num_ms': 256, 'dn_bw': 64, 'rn_bw': 64, 'print_stats': 1}
  Sweep     : {'T_M': [1, 2, 4], 'T_N': [1, 2], 'T_K': [32, 64, 128]}
  Total runs: 18
```

Run the validator standalone:

```bash
python3 -m sweep.validator sweep/configs/densegemm_sweep.yaml
```

Expected output:

```
Validation passed.
```

### Section 3 - Ify

Expander, command builder, and runner. Not built yet.

### Section 3 - Ify

Runner and CLI entry point. Not built yet.

---

## Contribution 2: Result Comparison Tool

### Section 1 - Samer

Scanner and stats parser.

`compare/scanner.py` walks the `experiment_runs/` directory, finds every run folder, and inventories the output files inside each one. It also extracts the sweep parameters (T_M, T_N, T_K) from the folder name and returns a list of records ready to be passed to the parser.

`compare/stats_parser.py` takes the two output files STONNE produces per run — a `.txt` JSON stats file and a `.counters` file — and extracts the key metrics from each. From the stats file it pulls cycles, bandwidth settings, and number of multiply-switch units. From the counters file it aggregates total wire writes, wire reads, FIFO pushes, and FIFO pops across all components.

To generate a real run folder to test against, run STONNE manually first:

```bash
mkdir -p experiment_runs/run_0001_TM2_TN1_TK64
cd stonne/stonne
./stonne -DenseGEMM -M=20 -N=20 -K=256 -num_ms=256 -dn_bw=64 -rn_bw=64 -T_K=64 -T_M=2 -T_N=1
cd ../..
```

Test the scanner:

```bash
python3 compare/scanner.py ./experiment_runs
```

Expected output:

```
Found 1 run(s) in ./experiment_runs

  Run     : run_0001_TM2_TN1_TK64
  Params  : {'TM': 2, 'TN': 1, 'TK': 64}
  Stats   : ./experiment_runs/run_0001_TM2_TN1_TK64/output_stats_...timestamp_....txt
  Counters: ./experiment_runs/run_0001_TM2_TN1_TK64/output_stats_...timestamp_....counters
```

Test the stats parser (replace filenames with the actual timestamped names in your run folder):

```bash
python3 compare/stats_parser.py \
  "experiment_runs/run_0001_TM2_TN1_TK64/output_stats_...timestamp_....txt" \
  "experiment_runs/run_0001_TM2_TN1_TK64/output_stats_...timestamp_....counters"
```

Expected output:

```
Stats:
  cycles: 6200
  dn_bw: 64
  rn_bw: 64
  num_ms: 256
  layer_type: 3

Counters:
  CB_WIRE_WRITE: 3200
  CB_WIRE_READ: 0
  FIFO_PUSH: 629046
  FIFO_POP: 628532
```

### Section 2 - Kobby

Energy wrapper and aggregator. Not built yet.

### Section 3 - Ify

CSV export and analyzer CLI. Not built yet.