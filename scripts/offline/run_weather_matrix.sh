#!/usr/bin/env bash

set -u
set -o pipefail

: "${V2XVERSE_ROOT:?Set V2XVERSE_ROOT to the V2Xverse repository}"
: "${OFFLINE_VIEW_ROOT:?Set OFFLINE_VIEW_ROOT to the directory containing weather/method model views}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
FUSION_METHOD="${FUSION_METHOD:-intermediate}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$V2XVERSE_ROOT/results/stage9b_offline_matrix}"
INFERENCE_ENTRY="${INFERENCE_ENTRY:-$V2XVERSE_ROOT/opencood/tools/inference_multiclass.py}"

METHODS=(
    baseline
    density
    density_doppler
    density_doppler_gate
)

WEATHERS=(
    OFF
    RF1
    RF2
    RF3
)

LOG_ROOT="$OUTPUT_ROOT/logs"
STATUS_FILE="$OUTPUT_ROOT/offline_matrix_status.tsv"

mkdir -p "$LOG_ROOT"
printf "weather\tmethod\trc\tmodel_dir\tlog\n" > "$STATUS_FILE"

expected=16
completed=0
passed=0
failed=0

echo "=== OFFLINE 16-CELL MATRIX ==="
echo "view_root=$OFFLINE_VIEW_ROOT"
echo "output_root=$OUTPUT_ROOT"
echo "expected_cells=$expected"
echo

if [ ! -f "$INFERENCE_ENTRY" ]; then
    echo "ERROR: inference entry not found: $INFERENCE_ENTRY"
    exit 2
fi

for weather in "${WEATHERS[@]}"; do
    for method in "${METHODS[@]}"; do
        model_dir="$OFFLINE_VIEW_ROOT/$weather/$method"
        log="$LOG_ROOT/${weather}_${method}.log"

        echo "START weather=$weather method=$method"

        if [ ! -d "$model_dir" ]; then
            rc=3
            echo "ERROR: model view missing: $model_dir" > "$log"
        else
            "$PYTHON_BIN" "$INFERENCE_ENTRY" \
                --model_dir "$model_dir" \
                --fusion_method "$FUSION_METHOD" \
                --note "_stage9b_${weather}_${method}" \
                > "$log" 2>&1
            rc=$?
        fi

        completed=$((completed + 1))

        if [ "$rc" -eq 0 ]; then
            passed=$((passed + 1))
            echo "PASS weather=$weather method=$method"
        else
            failed=$((failed + 1))
            echo "FAIL weather=$weather method=$method rc=$rc log=$log"
        fi

        printf "%s\t%s\t%s\t%s\t%s\n" \
            "$weather" "$method" "$rc" "$model_dir" "$log" \
            >> "$STATUS_FILE"
    done
done

echo
echo "=== SUMMARY ==="
echo "expected_cells=$expected"
echo "completed_cells=$completed"
echo "passed_cells=$passed"
echo "failed_cells=$failed"
echo "status_file=$STATUS_FILE"

if [ "$completed" -eq "$expected" ] && [ "$failed" -eq 0 ]; then
    echo "OFFLINE_MATRIX_STATUS=PASS"
    exit 0
fi

echo "OFFLINE_MATRIX_STATUS=PARTIAL"
exit 1
