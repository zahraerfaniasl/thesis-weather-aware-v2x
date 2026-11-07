# Stage-9b Offline Evaluation Configurations

This directory contains six portable offline configurations for the
`confirm3` Baseline and Density models.

Results for these models were located only for OFF and RF3, on the Town04
validation split and the seven-route Town05 test subset. No `confirm3`
result was located for RF2, so the two RF2 files are marked
`evaluation_status: no_confirm3_result_located`.

The four-method screening used different models. See
`configs/experiments/README.md`.

## Evaluation matrix

| Method | OFF | RF2 | RF3 |
|---|---:|---:|---:|
| Baseline | Result located | Configuration only | Result located |
| Radar density | Result located | Configuration only | Result located |

## Evaluation protocol

The audited evaluation protocol uses:

- confidence threshold: `0.20`;
- IoU thresholds: `0.30`, `0.50`, and `0.70`;
- validation split: `results/stage9b7_index/val`;
- fusion method: `intermediate`;
- training seed: `2029`;
- checkpoint: `net_epoch3.pth`.

The classes evaluated by the Stage-9b multiclass inference script are:

| Class | Class ID |
|---|---:|
| Vehicle | 0 |
| Pedestrian | 1 |
| Bicycle | 3 |

## Preprocessing

All six configurations use `SpVoxelPreprocessor` with:

- LiDAR range: `[-36, -12, -22, 36, 12, 14]`;
- voxel size: `[0.125, 0.125, 36]`;
- maximum points per voxel: `32`;
- maximum test voxels: `70000`;
- maximum training voxels: `32000`.

## Model checkpoints

The baseline model identifier is:

`stage9b_confirm3_baseline_seed2029_2026_09_14_18_47_05`

The density model identifier is:

`stage9b_confirm3_density_seed2029_2026_09_15_02_38_03`

The `confirm3` offline evaluation used `net_epoch3.pth`. The closed-loop
agent did not use this file: it loaded `net_epoch_bestval_at1.pth`, as the
run logs confirm (`resuming best validation model at epoch 1`). Offline and
closed-loop results therefore come from different checkpoints of the same
training run.

Checkpoint binaries are not copied into this repository.

Portable paths use the `V2XVERSE_ROOT` environment variable.

## Weather

The configurations cover OFF, RF2, and RF3. The weather definitions are
stored in `configs/weather/`.

OFF retains RF2 only as an inactive fallback profile; joint weather is
disabled in that condition.

## Radar modes

- baseline configurations use radar mode `none`;
- density configurations use radar mode `density`;
- density fusion type is `additive`.
