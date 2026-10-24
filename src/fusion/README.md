# Fusion modules

This directory contains the cooperative feature-fusion module used in the
thesis experiments.

## Implemented fusion method

Both the baseline and radar-density perception models use the CoDriving
multi-scale attention fusion module:

- Model: `center_point_codriving`
- Fusion implementation: `attention/codriving_attn.py`
- Aggregation operator: `ATTEN`
- Feature dimension: 256
- Input channels: 256
- Number of attention heads: 8
- Multi-scale fusion: enabled
- Attention-only mode: enabled
- Dropout rate: 0
- Maximum number of cooperative agents: 5

The fusion configuration is identical for the baseline and radar-density
models. Therefore, the difference between these models is not a change in
the cooperative attention architecture. The radar-density model additionally
integrates radar BEV information through the radar input and adaptation
pipeline.

The model-level radar integration is documented separately under
`src/integration/`.

## Directory structure

    fusion/
    ├── README.md
    ├── __init__.py
    └── attention/
        ├── __init__.py
        └── codriving_attn.py

## Attribution

The CoDriving attention module originates from the V2Xverse/OpenCOOD
codebase and is included to document and reproduce the fusion architecture
used in the thesis experiments.

See the repository-level `THIRD_PARTY_NOTICES.md` and the original project
license for attribution and licensing details.

The module requires a compatible V2Xverse installation. See `environment/`.
