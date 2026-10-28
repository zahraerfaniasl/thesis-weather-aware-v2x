# Stage-9b Offline Evaluation Configurations

This directory contains the six portable configurations for the final
Stage-9b offline evaluation matrix.

## Evaluation matrix

| Method | OFF | RF2 | RF3 |
|---|---:|---:|---:|
| Baseline | Yes | Yes | Yes |
| Radar density | Yes | Yes | Yes |

## Evaluation protocol

The audited evaluation protocol uses:

- confidence threshold: `0.20`;
- IoU thresholds: `0.30`, `0.50`, and `0.70`;
- validation split: `results/stage9b7_index/val`;
- fusion method: `intermediate`;
- training seed: `2029`;
- checkpoint policy: branch `net_epoch1.pth`.

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

The final validation drivers explicitly select `net_epoch1.pth`.
Checkpoint binaries are not copied into this repository.

Portable paths use the `V2XVERSE_ROOT` environment variable.

## Weather

Each method is evaluated under OFF, RF2, and RF3. The weather definitions
are stored in `configs/weather/`.

OFF retains RF2 only as an inactive fallback profile; joint weather is
disabled in that condition.

## Radar modes

- baseline configurations use radar mode `none`;
- density configurations use radar mode `density`;
- density fusion type is `additive`.
