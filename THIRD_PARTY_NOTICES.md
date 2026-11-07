# Third-party notices

This project depends on, or was informed by, the works below. Each work
stays under its own terms. License information was checked on 2026-11-07.

## Summary

| Work | Terms found | Use here | Status |
|---|---|---|---|
| V2Xverse | No repository license | Base platform | Permission requested: pending |
| OpenCOOD | Academic Software License, UCLA Mobility Lab | Base of the perception code | Permission requested: pending |
| LISA | GPL-3.0 | Rain sampling logic | Review needed |
| LiDAR_fog_sim | CC BY-NC 4.0 | Fog response tables | Attribution given, non-commercial |
| CARLA leaderboard, scenario_runner | Own license files | Closed-loop evaluation | Not redistributed here |
| CARLA 0.9.10 | Own license | Simulator | Not redistributed here |

## V2Xverse

- Project: https://github.com/CollaborativePerception/V2Xverse
- Compared revision: `b627175`
- Paper: Liu et al., "Towards Collaborative Autonomous Driving: Simulation
  Platform and End-to-End System", arXiv:2404.09496

The repository has no top-level license file, and 83 of its Python files carry
the header `License: TDG-Attribution-NonCommercial-NoDistrib`.

The following material derives from V2Xverse or contains parts of it:

- `src/weather_augmentation/integration/*.patch`
- `configs/closed_loop/*.yaml`

The unmodified `codriving_attn.py` was removed from this repository.
Modified V2Xverse source files are not included.

## OpenCOOD

- Project: https://github.com/DerrickXuNu/OpenCOOD
- License: Academic Software License, (c) 2021 UCLA Mobility Lab

V2Xverse builds on OpenCOOD. The license limits use to educational or academic
research, and prohibits transferring the software or derivatives to others
without further permission. `configs/offline/*.yaml` follow the OpenCOOD
configuration format.

## LISA

- Project: https://github.com/velatkilic/LISA
- License: GPL-3.0

`src/weather_augmentation/joint_weather_rain_sampler_stage9b.py` follows the
LISA strongest-return sampling logic. If this file is a derivative work, it
must be distributed under GPL-3.0.

## LiDAR_fog_sim

- Project: https://github.com/MartinHahner/LiDAR_fog_sim
- License: Creative Commons Attribution-NonCommercial 4.0 International
- Paper: Hahner et al., "Fog Simulation on Real LiDAR Point Clouds for 3D
  Object Detection in Adverse Weather", ICCV 2021

The tables in `src/weather_augmentation/tables/` were built with reference to
this project's `theory.py` and `fog_simulation.py`, and the implementation
was changed for joint rain and fog. These tables may not be used commercially.

## Other projects

V2Xverse acknowledges CARLA leaderboard, scenario_runner, InterFuser (Apache-2.0),
and HEAL. Their code is not redistributed directly here, and any future patch
touching their files must keep their notices.
