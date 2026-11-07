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

## Status

In the final closed-loop run, the Density perception model received an
all-zero radar input, because `stage9b_online_radar` was `false`. The closed-loop
modules below produced logs and monitoring outputs only. See
`configs/radar/README.md`.

The modules import `opencood.data_utils.radar.*`, so they do not run on their
own. They are placed in that package of a V2Xverse tree.

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

The upstream files that call these modules are not duplicated here. They are
listed in `src/integration/README.md`.

## Upstream project

These modules come from the thesis working tree based on V2Xverse/OpenCOOD
and do not exist in upstream V2Xverse. Third-party components remain subject
to their original licenses. See `THIRD_PARTY_NOTICES.md`.

The modules require a compatible V2Xverse installation. See `environment/`
and the repository installation instructions.
