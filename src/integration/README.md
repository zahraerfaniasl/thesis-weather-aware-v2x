# V2Xverse Integration

This directory is the central index for the integration artifacts used to
connect the portable thesis components to V2Xverse.

## Joint weather integration

The Stage-9b joint-weather integration artifacts are maintained alongside
the weather package:

- `../weather_augmentation/integration/pnp_agent_joint_weather_override.patch`
- `../weather_augmentation/integration/v2xverse_basedataset_joint_weather.patch`
- `../weather_augmentation/integration/SOURCE_INTEGRATION_SHA256SUMS.txt`
- `../weather_augmentation/integration/README.md`

The two patches reproduce the audited modifications to:

- `simulation/leaderboard/team_code/pnp_agent_e2e.py`
- `opencood/data_utils/datasets/basedataset/v2xverse_basedataset.py`

The original V2Xverse source files are not duplicated in this repository.

These patches apply to the thesis working tree, not to a clean V2Xverse
checkout: both fail to apply forward on upstream commit `b627175`, because
that tree lacks the radar changes they sit on. Reverse application on the
thesis snapshot succeeds.

## Radar integration (not yet packaged)

The model-level radar integration is not in this repository yet, because it
consists of changes to V2Xverse and OpenCOOD source files. It will be added
as one cumulative patch against upstream commit `b627175` once redistribution
permission is confirmed (see `THIRD_PARTY_NOTICES.md`).

| Upstream file | Changed lines | Role |
|---|---:|---|
| `opencood/models/center_point_codriving.py` | 194 | Radar adapter and feature fusion |
| `opencood/data_utils/datasets/intermediate_multiclass_fusion_dataset.py` | 83 | Radar BEV input |
| `opencood/data_utils/datasets/basedataset/v2xverse_basedataset.py` | 118 | Radar paths and joint weather |
| `opencood/tools/train.py` | 70 | Training changes |
| `opencood/tools/inference_multiclass.py` | 164 | Multiclass evaluation |
| `simulation/leaderboard/team_code/pnp_agent_e2e.py` | 831 | Closed-loop agent |
| `simulation/leaderboard/team_code/pnp_infer_action_e2e.py` | 1476 | Closed-loop inference and traces |
| `simulation/leaderboard/leaderboard/sensors/fixed_sensors.py` | 766 | RSU sensors |
| `simulation/leaderboard/leaderboard/envs/sensor_interface.py` | 139 | Sensor data interface |

Changed lines are counted with `diff -w`, as added plus removed lines.
