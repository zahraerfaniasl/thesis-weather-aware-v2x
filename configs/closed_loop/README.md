# Final closed-loop configurations

This directory contains the portable configurations used in the confirmed Stage-9b closed-loop experiment matrix.

## Experiment matrix

The matrix contains the `baseline` and `density` methods under three weather conditions: `OFF`, `RF2`, and `RF3`.

All 18 configurations use training seed `2029` and cover the confirmed `8_10`, `5_10`, and `5_50` families.

| Method | OFF | RF2 | RF3 |
|---|---:|---:|---:|
| baseline | included | included | included |
| density | included | included | included |

All three families are included because they were used by the final five-part batch evaluation.

## Five-part batch mapping

| Evaluation part | Configuration family |
|---|---|
| `1s` | `8_10` |
| `2s` | `5_10` |
| `3s` | `5_10` |
| `4s` | `8_10` |
| `5s` | `5_50` |

## Model paths

Baseline configurations contain this replacement marker:

`REPLACE_WITH_BASELINE_PERCEPTION_MODEL_DIR`

Density configurations contain this replacement marker:

`REPLACE_WITH_DENSITY_PERCEPTION_MODEL_DIR`

Replace the appropriate marker with the trained perception-model directory before execution.

The planner checkpoint uses this relative path:

`checkpoints/codriving/planner/codriving_planner.ckpt`

Model weights are not included in this repository.

## Weather selection

| Condition | enabled | profile |
|---|---:|---|
| OFF | false | RF2 (inactive placeholder) |
| RF2 | true | RF2 |
| RF3 | true | RF3 |

The OFF configurations keep `profile: RF2`, but augmentation is not applied because `enabled` is `false`.

The legacy `legacy_rsu_rain` mechanism is disabled in all six configurations to prevent double weather degradation.

## Portability and provenance

The configurations contain no original machine-specific V2Xverse paths.

Original source filenames and SHA-256 hashes are recorded in `SOURCE_CONFIG_SHA256SUMS.txt`.

The shared weather configuration is stored in `../weather/joint_weather_base.yaml`.

The portable implementation and response tables are stored in `../../src/weather_augmentation/`.
