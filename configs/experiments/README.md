# Stage-9b experiment matrices

This directory records the experimental design used for offline method
selection and final closed-loop evaluation.

## Offline screening

The offline screening consisted of sixteen evaluations:

- four methods;
- four weather conditions;
- one evaluation for each method and weather pair.

The evaluated methods were:

1. Baseline without radar fusion;
2. Density;
3. Density + Doppler;
4. Density + Doppler + Gate.

Each method was evaluated under `OFF`, `RF1`, `RF2`, and `RF3`.

Baseline was the reference method. The other three methods were radar
fusion candidates.

All four methods completed training and all sixteen evaluations. Density
was selected because it had the highest mAP@0.3 and mAP@0.5 under every
weather condition. It was not the best method at mAP@0.7 under OFF, RF1,
or RF2.

The screening used the `stage9b_clean_*_pilot_20260912` models on the
six-route Town04 validation split. Its manifest records no training seed
or checkpoint file name. These are not the `confirm3` models used later.

The complete sixteen-cell design is recorded in
`offline_screening_matrix.yaml`.

## Final closed-loop evaluation

The final closed-loop matrix contained:

- Baseline and Density;
- weather conditions `OFF`, `RF2`, and `RF3`;
- configuration families `8_10`, `5_10`, and `5_50`;
- training seed `2029`.

The route-part mapping was:

| Part | Configuration family |
|---|---|
| `1s` | `8_10` |
| `2s` | `5_10` |
| `3s` | `5_10` |
| `4s` | `8_10` |
| `5s` | `5_50` |

There are eighteen unique packaged closed-loop configurations:

`2 methods x 3 weather conditions x 3 configuration families = 18`.

RF1 was used during offline screening but was not included in the final
closed-loop weather matrix.

Each cell has 85 jobs over 58 unique route IDs. The summaries count 73 jobs
per cell: the same 12 jobs have no ego-level result record in all six cells.

The closed-loop agent loaded `net_epoch_bestval_at1.pth`. The Density
perception input from radar was all zeros in this run, so these results do
not evaluate radar fusion. See `configs/radar/README.md`.

## Configuration availability

The repository contains operational offline configurations for the final
Baseline and Density methods under `OFF`, `RF2`, and `RF3`.

Separate operational YAML files for every cell of the earlier screening
matrix are not reproduced because their exact audited source variants
have not been packaged. No missing parameter values were guessed.

This directory records the experimental design and selection decision.
The numerical results are stored in `results/`.
