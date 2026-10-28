# Stage-9b Joint Weather Configurations

This directory contains the portable weather configurations used by the final Stage-9b evaluation matrix.

## Conditions

| Condition | Enabled | Profile | Rain rate | Fog extinction | Rain extinction | Total extinction | Fog backscatter |
|---|---:|---|---:|---:|---:|---:|---:|
| OFF | No | RF2 fallback only | 0 mm/h | 0 | 0 | 0 | 0 |
| RF2 | Yes | RF2 | 50 mm/h | 0.06 1/m | 0.004314408151764052 1/m | 0.06431440815176405 1/m | 0.000921310633919122 |
| RF3 | Yes | RF3 | 50 mm/h | 0.20 1/m | 0.004314408151764052 1/m | 0.20431440815176408 1/m | 0.0030710354463970736 |

RF2 and RF3 use the same rain rate. RF3 represents the stronger condition because its fog extinction and fog backscatter are substantially higher.

The OFF configuration keeps `profile: RF2` as an inactive fallback value, but weather augmentation is disabled by `enabled: false`.

## Common runtime settings

| Setting | Value |
|---|---|
| Manifest | `src/weather_augmentation/tables/manifest.json` |
| Minimum return power (`pmin`) | `2.25e-05` |
| Runtime backscatter scale (`beta0`) | `3.1830988618379064e-07` |
| Base seed | `2026` |
| Seed policy | `content_role_v1` |

The runtime `beta0` setting is distinct from the profile-specific `beta_fog` values stored in the response-table manifest.

## Response-table integrity

| Profile | Table | SHA-256 |
|---|---|---|
| RF2 | `RF2.npz` | `a323bc0a486e3a1c45601de145d9d23eabaae72f11f2e2aed30fd859d942792d` |
| RF3 | `RF3.npz` | `437f7a7cf4e2af119ff1ecbeb7638f8cfd74a4930a7bb594c51726bc1d6d7798` |

RF1 remains in the portable table package as a reference profile, but the final closed-loop matrix uses OFF, RF2, and RF3.

## Weather exclusivity

The legacy dataset-level `adverse_weather` mechanism is disabled in all three files. The closed-loop configurations also disable `legacy_rsu_rain`, preventing two weather degradation mechanisms from running simultaneously.

## Files

- `OFF.yaml`: joint weather disabled.
- `RF2.yaml`: moderate joint rain-fog condition.
- `RF3.yaml`: stronger fog condition with the same rain rate as RF2.
- `joint_weather_base.yaml`: reusable base configuration fragment.
