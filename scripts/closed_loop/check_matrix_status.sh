#!/usr/bin/env bash

set -u

: "${V2XVERSE_ROOT:?Set V2XVERSE_ROOT to the upstream V2Xverse repository}"

RESULTS_ROOT="${RESULTS_ROOT:-$V2XVERSE_ROOT/results}"
MATRIX_ROOT="${MATRIX_ROOT:-$RESULTS_ROOT/stage9b_final_matrix_20260917}"

cells=(
    stage9b_final_baseline_OFF
    stage9b_final_baseline_RF2
    stage9b_final_baseline_RF3
    stage9b_final_density_OFF
    stage9b_final_density_RF2
    stage9b_final_density_RF3
)

parts=(1s 2s 3s 4s 5s)

expected_logs=30
present_logs=0
nonempty_logs=0
missing_logs=0

echo "=== CLOSED-LOOP MATRIX STATUS ==="
echo "matrix_root=$MATRIX_ROOT"
echo

for cell in "${cells[@]}"; do
    cell_present=0

    for part in "${parts[@]}"; do
        log="$MATRIX_ROOT/${cell}_${part}.log"

        if [ -f "$log" ]; then
            present_logs=$((present_logs + 1))
            cell_present=$((cell_present + 1))

            if [ -s "$log" ]; then
                nonempty_logs=$((nonempty_logs + 1))
            fi
        else
            missing_logs=$((missing_logs + 1))
            echo "MISSING_LOG=$log"
        fi
    done

    result_dir="$RESULTS_ROOT/results_driving_${cell}"

    if [ -d "$result_dir" ]; then
        result_status=present
    else
        result_status=missing
    fi

    echo "CELL=$cell logs=${cell_present}/5 results=$result_status"
done

controller="$MATRIX_ROOT/controller.log"

if [ -f "$controller" ]; then
    controller_status=present
else
    controller_status=missing
fi

if [ -f "$controller" ] && grep -q "FINAL_MATRIX_FINISHED=YES" "$controller"; then
    completion_marker=yes
else
    completion_marker=no
fi

echo
echo "=== SUMMARY ==="
echo "expected_part_logs=$expected_logs"
echo "present_part_logs=$present_logs"
echo "nonempty_part_logs=$nonempty_logs"
echo "missing_part_logs=$missing_logs"
echo "controller_log=$controller_status"
echo "completion_marker=$completion_marker"

if [ "$present_logs" -eq "$expected_logs" ] && [ "$missing_logs" -eq 0 ]; then
    echo "MATRIX_LOG_STATUS=PASS"
else
    echo "MATRIX_LOG_STATUS=INCOMPLETE"
    exit 1
fi
