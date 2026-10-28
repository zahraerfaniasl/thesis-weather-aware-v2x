# Radar configurations

This directory contains the portable radar configuration used by the
final Stage-9b experiments.

## Configuration layers

Radar operation has two separate layers:

1. RSU radar capture in the closed-loop agent.
2. Radar feature fusion in the perception model.

RSU radar capture was enabled for both baseline and density experiments.
The two methods differ in whether the perception model consumes the radar
feature.

| Configuration | RSU capture | Perception mode | Radar feature consumed |
|---|---:|---|---:|
| `radar_off.yaml` | enabled | `none` | no |
| `radar_density.yaml` | enabled | `density` | yes |

The `stage9b_online_radar: false` model setting does not mean that the
closed-loop RSU radar sensor was disabled. Raw radar logging, BEV
generation, and oracle monitoring remained enabled.

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

All paths in these files are repository-relative.
