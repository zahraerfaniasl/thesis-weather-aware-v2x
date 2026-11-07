# Radar configurations

This directory contains the portable radar configuration used by the
final Stage-9b experiments.

## Configuration layers

Radar operation has two separate layers:

1. RSU radar capture in the closed-loop agent.
2. Radar feature fusion in the perception model.

RSU radar capture was enabled for both baseline and density experiments.
The two methods have different perception modes, but radar input reached
the perception model only in the offline evaluation.

| Configuration | RSU capture | Perception mode | Radar input offline | Radar input closed loop |
|---|---:|---|---:|---:|
| `radar_off.yaml` | enabled | `none` | no | no |
| `radar_density.yaml` | enabled | `density` | yes | no (see below) |

## Known limitation of the final closed-loop run

The Density model configuration has `stage9b_online_radar: false`. With
this setting, the closed-loop path filled neither `radar_path` nor the
online radar packet, so the `radar_bev` tensor passed to the perception
model was all zeros at every step.

The RSU radar sensor itself stayed active: raw logging, BEV generation,
and oracle monitoring all ran. Those outputs were not model inputs.

The final closed-loop Density results are therefore **not an evaluation of
radar fusion**. They compare two differently trained checkpoints.

This conclusion comes from the code and configuration. Radar input tracing
was not active in that run, so it still needs a trace-based check on the
server.

## Radar oracle

The radar oracle was enabled for monitoring and logging. Its safety
override was disabled, so it did not replace or modify the final vehicle
control command.

## Sensor parameters

The final sensor and BEV parameters are recorded in
`radar_sensor_parameters.yaml`.

Important values include:

- range: 100 m;
- horizontal field of view: 120 degrees;
- vertical field of view: 30 degrees;
- points per second: 30000;
- sensor tick: 0.05 seconds;
- BEV resolution: 0.25 m;
- BEV extents: 36 m front, 12 m rear, 12 m left, and 12 m right;
- maximum points per BEV cell: 5.

These parameters describe the final Stage-9b run. Its radar was mounted with
pitch 0 and a fixed yaw of -90 degrees. An analysis after the run estimated
that this mounting covers about 13% of the ego BEV
(`docs/stage2_summary.md`), so the radar design is being revised.

All paths in these files are repository-relative.
