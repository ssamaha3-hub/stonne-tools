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

Expander and command builder.

`sweep/expander.py` takes the parsed config and computes the Cartesian product of all sweep parameter lists. For each combination it merges the fixed and sweep params into one flat dict and assigns a run ID, a human-readable run name, and an output directory path. The run names match the format the scanner expects — for example `run_0001_TM1_TN1_TK32`.

`sweep/command_builder.py` takes a run spec from the expander and builds the STONNE CLI command as a list of strings ready for `subprocess.run()`. For DenseGEMM it produces a command like `["./stonne/stonne", "-DenseGEMM", "-M=20", "-N=20", "-K=256", "-num_ms=256", "-dn_bw=64", "-rn_bw=64", "-T_M=1", "-T_N=1", "-T_K=32"]`.

Preview the expanded runs:

```bash
python3 -m sweep.expander sweep/configs/densegemm_sweep.yaml
```

Expected output:

```
Total runs: 18

  run_0001_TM1_TN1_TK32
    params     : {'M': 20, 'N': 20, 'K': 256, 'num_ms': 256, 'dn_bw': 64, 'rn_bw': 64, 'print_stats': 1, 'T_M': 1, 'T_N': 1, 'T_K': 32}
    output_dir : ./experiment_runs/run_0001_TM1_TN1_TK32

  run_0002_TM1_TN1_TK64
    ...
```

Preview the built commands:

```bash
python3 -m sweep.command_builder sweep/configs/densegemm_sweep.yaml
```

Expected output:

```
Total commands: 18

  run_0001_TM1_TN1_TK32
    ./stonne/stonne -DenseGEMM -M=20 -N=20 -K=256 -num_ms=256 -dn_bw=64 -rn_bw=64 -print_stats=1 -T_M=1 -T_N=1 -T_K=32

  run_0002_TM1_TN1_TK64
    ...
```

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