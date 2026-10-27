# V2Xverse Joint-Weather Integration

This directory documents the integration of the portable Stage-9b
joint rain-fog LiDAR augmentation with V2Xverse.

## Provenance

The audited V2Xverse source directory was not a Git worktree.
Therefore, historical Git commits were unavailable.

`SOURCE_INTEGRATION_SHA256SUMS.txt` records the exact SHA-256
hashes of the audited bridge, dataset, and PnP-agent files.

## Runtime flow

1. The PnP agent loads the perception configuration.
2. `stage9b_joint_weather_override` selects OFF, RF2, or RF3.
3. The merged weather configuration is validated.
4. The dataset loads each LiDAR point cloud.
5. The dataset calls `apply_joint_weather(self, lidar, agent)`.
6. The sensor role is included in deterministic seeding.

## Audited sensor roles

- `ego`: controlled ego vehicle
- `other_ego`: collaborating vehicle
- `rsu`: roadside unit

These roles are part of the `content_role_v1` seed policy.

## Weather exclusivity

Joint weather must not run simultaneously with legacy weather.
Both dataset-level `adverse_weather` and agent-level
`legacy_rsu_rain` must remain disabled.

## Portable files

The implementation is stored in `src/weather_augmentation/`.
Response tables and manifests are stored in its `tables/` directory.
`manifest.json` uses portable relative table paths.
`manifest.provenance.json` preserves the original provenance data.

## Closed-loop configurations

Portable templates are provided for baseline and density methods
under OFF, RF2, and RF3 weather conditions.

Model-directory placeholders must be replaced before execution.

## Reproducibility

Table hashes, profile loading, deterministic seeds, role-specific
seeds, and package imports were smoke-tested successfully.
