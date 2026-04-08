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

`sweep/config_parser.py` reads that YAML, validates all required fields are present, and returns a clean dictionary the rest of the sweep engine can use.

Run the parser:

```bash
python3 sweep/config_parser.py sweep/configs/densegemm_sweep.yaml
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

### Section 2 - Kobby

Expander and command builder. Not built yet.

### Section 3 - Ify

Runner and CLI entry point. Not built yet.

---

## Contribution 2: Result Comparison Tool

### Section 1 - Samer

Scanner and stats parser. Not built yet.

### Section 2 - Kobby

Energy wrapper and aggregator. Not built yet.

### Section 3 - Ify

CSV export and analyzer CLI. Not built yet.