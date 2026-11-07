#!/usr/bin/env bash
set -euo pipefail

cd "${V2XVERSE_ROOT:?Set V2XVERSE_ROOT to the V2Xverse tree}" || exit 1

MODE="${1:-}"
PY="${PYTHON:-python}"
CONFIG_DIR="opencood/hypes_yaml/v2xverse/radar_ablation"

case "$MODE" in
    baseline|density|density_doppler) ;;
    *)
        echo "USAGE: $0 baseline|density|density_doppler"
        exit 2
        ;;
esac

if pgrep -f 'stage9b7_collect_raw.sh|leaderboard_evaluator_parameter.py|CarlaUE4' \
    >/dev/null; then
    echo "ERROR: COLLECTION_OR_CARLA_IS_ACTIVE"
    echo "Training was not started."
    exit 3
fi

CONFIG="$CONFIG_DIR/${MODE}.yaml"
test -f "$CONFIG" || {
    echo "ERROR: missing $CONFIG"
    exit 4
}

"$PY" scripts/stage9b15_refresh_index.py

STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="results/training_logs/${MODE}_${STAMP}"
mkdir -p "$LOG_DIR"

cp -a "$CONFIG" "$LOG_DIR/config.yaml"

sha256sum \
    "$CONFIG" \
    opencood/models/center_point_codriving.py \
    opencood/data_utils/radar/radar_bev.py \
    >"$LOG_DIR/source_hashes.txt"

echo "MODE=$MODE"
echo "CONFIG=$CONFIG"
echo "LOG_DIR=$LOG_DIR"
echo "TRAINING_START=$(date -Is)"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

"$PY" opencood/tools/train.py \
    --hypes_yaml "$CONFIG" \
    --fusion_method intermediate \
    2>&1 | tee "$LOG_DIR/train.log"
