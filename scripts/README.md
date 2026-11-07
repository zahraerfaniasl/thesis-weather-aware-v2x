# Experiment scripts

These are the training and experiment drivers written for Stage-9b. They run
inside a modified V2Xverse tree, so they do not run from this repository
alone.

Set these variables first:

```bash
export V2XVERSE_ROOT=/path/to/V2Xverse
export PYTHON=/path/to/python
```

| Script | Purpose |
|---|---|
| `train_baseline.sh`, `train_density.sh`, `train_density_doppler.sh` | Start one training run |
| `stage9b18_train_ablation.sh` | Shared training driver |
| `stage9b32b_branch_finetune_all.py` | Fine-tune all method branches from one shared initialization |
| `stage9b_validate_branches.py` | Evaluate the trained branches |
| `stage9b_run_final_matrix_20260917.sh` | Run the 510-job closed-loop matrix |

Compared with the versions used on the server, only the hard-coded paths were
replaced with these variables. The edited scripts passed syntax checks but
were not run again.

The closed-loop matrix also calls `scripts/batch_eval_driving_e2e.sh` from
V2Xverse. That file is not copied here.
