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
The integration patches were verified using forward and reverse patch tests.

## Other subsystems

Integration artifacts for radar or fusion can be referenced here if they
are packaged later.
