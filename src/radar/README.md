# Radar integration

This directory contains the radar-processing components developed or
adapted for the thesis experiments built on V2Xverse/OpenCOOD.

## Runtime data flow

The offline/data-pipeline integration follows:

`intermediate_multiclass_fusion_dataset.py`
→ `radar_online_packet_stage9b.py`
→ `radar_runtime_stage9b.py`

The closed-loop agent integration uses:

`pnp_agent_e2e.py`
→ `rsu_radar_bev.py`
→ `rsu_radar_bev_warp.py`

The agent also uses `oracle/rsu_radar_oracle.py` for idealized reference
observation and logging.

## Files

- `radar_bev.py`: converts radar measurements into BEV representations.
- `radar_runtime_stage9b.py`: prepares runtime radar channels and features.
- `radar_online_packet_stage9b.py`: prepares online radar packets for the
  OpenCOOD dataset pipeline.
- `rsu_radar_bev.py`: constructs and optionally logs the RSU-frame radar BEV.
- `rsu_radar_bev_warp.py`: transforms the RSU radar BEV into the Ego frame.
- `oracle/rsu_radar_oracle.py`: provides idealized reference radar
  observations and logging for evaluation.

## Oracle configuration

In the inspected final Stage9B configurations:

- `radar_oracle.enabled` was set to `true`.
- `radar_oracle.safety_override.enabled` was set to `false`.
- `stage9b_closed_loop_metadata.safety_override` was set to `false`.

Therefore, the Oracle component was enabled for reference observation and
logging, but the safety override was disabled and was not intended to
modify the vehicle control commands.

## Integration files

The following integration files are not duplicated in this directory and
will be documented separately under `src/integration/` or `patches/`:

- `opencood/data_utils/datasets/intermediate_multiclass_fusion_dataset.py`
- `simulation/leaderboard/team_code/pnp_agent_e2e.py`

## Upstream project

These modules were copied or adapted from the thesis working tree based on
V2Xverse/OpenCOOD. Third-party components remain subject to their original
licenses. See `THIRD_PARTY_NOTICES.md`.

The modules require a compatible V2Xverse installation. See `environment/`
and the repository installation instructions.
