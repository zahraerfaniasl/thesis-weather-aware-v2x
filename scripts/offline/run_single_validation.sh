#!/usr/bin/env bash
set -u


METHOD="${1:-}"
MODEL_DIR="${2:-}"
FUSION_METHOD="${3:-intermediate}"

: "${V2XVERSE_ROOT:?Set V2XVERSE_ROOT to the V2Xverse repository}"
cd "$V2XVERSE_ROOT" || exit 1
PY="${PYTHON_BIN:-python3}"
TOOLS="$V2XVERSE_ROOT/opencood/tools"

case "$METHOD" in
    baseline|density|density_doppler|density_doppler_gate) ;;
    *)
        echo "USAGE: $0 baseline|density|density_doppler|density_doppler_gate MODEL_DIR [FUSION_METHOD]"
        exit 2
        ;;
esac

if [ ! -d "$MODEL_DIR" ]; then
    echo "ERROR: MODEL_DIR not found: $MODEL_DIR"
    exit 3
fi

if ! find "$MODEL_DIR" -maxdepth 1 -type f \
    -name 'net_epoch*.pth' -print -quit \
    | grep -q .; then
    echo "ERROR: No checkpoint found in $MODEL_DIR"
    exit 4
fi

LOG_DIR="$MODEL_DIR/stage9b_openloop_logs"
STATUS_FILE="$LOG_DIR/status.tsv"

mkdir -p "$LOG_DIR"

if [ ! -f "$STATUS_FILE" ]; then
    printf 'method\ttest\tvalue\trc\tlog\n' >"$STATUS_FILE"
fi

run_test() {
    local test_name="$1"
    local value="$2"
    shift 2

    local safe_value
    safe_value=$(echo "$value" | tr './ ' '___')

    local log="$LOG_DIR/${test_name}_${safe_value}.log"

    echo "START METHOD=$METHOD TEST=$test_name VALUE=$value"

    env \
      OMP_NUM_THREADS=2 \
      MKL_NUM_THREADS=2 \
      PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 \
      "$PY" "$@" >"$log" 2>&1

    local rc=$?

    printf '%s\t%s\t%s\t%s\t%s\n' \
      "$METHOD" "$test_name" "$value" "$rc" "$log" \
      >>"$STATUS_FILE"

    if [ "$rc" -eq 0 ]; then
        echo "PASS METHOD=$METHOD TEST=$test_name VALUE=$value"
    else
        echo "FAIL METHOD=$METHOD TEST=$test_name VALUE=$value RC=$rc LOG=$log"
        tail -n 15 "$log"
    fi

    return 0
}

run_test standard nominal \
  "$TOOLS/inference_multiclass.py" \
  --model_dir "$MODEL_DIR" \
  --fusion_method "$FUSION_METHOD" \
  --note "_stage9b_${METHOD}_standard"

for THRESHOLD in \
    0.000 \
    0.001 \
    0.003 \
    0.010 \
    0.020 \
    0.100 \
    1.000
do
    run_test communication "$THRESHOLD" \
      "$TOOLS/inference_multiclass_comm.py" \
      --model_dir "$MODEL_DIR" \
      --fusion_method "$FUSION_METHOD" \
      --comm_thre "$THRESHOLD" \
      --note "_stage9b_${METHOD}_comm_${THRESHOLD}"
done

run_test latency gaussian \
  "$TOOLS/inference_multiclass_latency.py" \
  --model_dir "$MODEL_DIR" \
  --fusion_method "$FUSION_METHOD" \
  --note "_stage9b_${METHOD}"

run_test pose_noise gaussian \
  "$TOOLS/inference_multiclass_w_noise.py" \
  --model_dir "$MODEL_DIR" \
  --fusion_method "$FUSION_METHOD" \
  --note "_stage9b_${METHOD}"

FAIL_COUNT=$(
    awk -F'\t' 'NR>1 && $4 != 0 {count++} END {print count+0}' \
      "$STATUS_FILE"
)

echo "METHOD=$METHOD"
echo "STATUS_FILE=$STATUS_FILE"
echo "FAIL_COUNT=$FAIL_COUNT"

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "OPENLOOP_EVALUATION=PASS"
    exit 0
else
    echo "OPENLOOP_EVALUATION=PARTIAL"
    exit 20
fi

# STAGE9B_GATE_PIPELINE_PATCH
