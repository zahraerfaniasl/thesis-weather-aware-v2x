# Offline evaluation scripts

This directory packages portable utilities for the Stage-9b offline screening protocol.

## Final screening matrix

The documented final protocol contains 16 evaluation cells:

- methods: `baseline`, `density`, `density_doppler`, and `density_doppler_gate`;
- conditions: `OFF`, `RF1`, `RF2`, and `RF3`;
- confidence threshold: `0.20`;
- IoU thresholds: `0.30`, `0.50`, and `0.70`;
- classes: Vehicle, Pedestrian, and Bicycle.

The selected candidate for final closed-loop evaluation was `density`.

## Files

- `run_single_validation.sh`: portable adaptation of the historical single-method offline runner.
- `run_weather_matrix.sh`: reconstructed runner for the documented 4-by-4 final screening matrix.
- `audit_offline_matrix.py`: validates the 16-cell status file and corresponding logs.
- `extract_fixed_confidence_metrics.py`: validates threshold `0.20` and extracts AP30, AP50, and AP70 for three classes.
- `SOURCE_OFFLINE_SHA256SUMS.txt`: hashes of the inspected upstream scripts.

## Usage

```bash
export V2XVERSE_ROOT=/path/to/V2Xverse
export PYTHON_BIN=python3

bash scripts/offline/run_single_validation.sh METHOD MODEL_DIR intermediate
```

For the complete matrix:

```bash
export OFFLINE_VIEW_ROOT=/path/to/offline/views
bash scripts/offline/run_weather_matrix.sh

python3 scripts/offline/audit_offline_matrix.py \\
    --output-root /path/to/stage9b_offline_matrix

python3 scripts/offline/extract_fixed_confidence_metrics.py \\
    --view-root "$OFFLINE_VIEW_ROOT"
```

The expected view layout is `WEATHER/METHOD`, for example `RF2/density`.

## Provenance

`run_single_validation.sh` is derived from the audited historical `stage9b29_openloop_eval.sh` runner, with machine-specific paths replaced by environment variables.

The inspected historical weather scripts used `clear`, `moderate`, and `severe`, forming a separate 12-cell sweep. They are not represented as the final 16-cell runner.

`run_weather_matrix.sh`, `audit_offline_matrix.py`, and `extract_fixed_confidence_metrics.py` are repository-side reproducibility utilities reconstructed from the final protocol recorded under `configs/experiments/`.

No historical `openloop_metrics.tsv` or `AP030507.yaml` artifacts were found during packaging. Therefore the extractor was validated structurally but was not run against historical result files.
