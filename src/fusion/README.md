# Fusion modules

This directory documents the cooperative feature-fusion settings used in
the thesis experiments. The fusion source file is not included here.

## Fusion method

Both the baseline and radar-density perception models use the CoDriving
multi-scale attention fusion module from V2Xverse:

- Model: `center_point_codriving`
- Upstream file: `opencood/models/fuse_modules/codriving_attn.py`
- Aggregation operator: `ATTEN`
- Feature dimension: 256
- Input channels: 256
- Number of attention heads: 8
- Multi-scale fusion: enabled
- Attention-only mode: enabled
- Dropout rate: 0
- Maximum number of cooperative agents: 5

The fusion configuration is identical for both models. The radar-density
model adds a radar adapter before this stage, so the difference between
the models is not in the cooperative attention architecture.

In the final closed-loop run, the radar input to that adapter was all zeros.
See `configs/radar/README.md`.

## Why the source file is absent

The file was not modified for this thesis, and V2Xverse has no repository
license that grants redistribution. Use it from the upstream project:
https://github.com/CollaborativePerception/V2Xverse

See `THIRD_PARTY_NOTICES.md`.
