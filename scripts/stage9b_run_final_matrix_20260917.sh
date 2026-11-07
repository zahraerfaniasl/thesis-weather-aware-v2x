#!/usr/bin/env bash

cd "${V2XVERSE_ROOT:?Set V2XVERSE_ROOT to the V2Xverse tree}" || exit 1

MATRIX_ROOT="results/stage9b_final_matrix_20260917"
mkdir -p "$MATRIX_ROOT"

echo "FINAL_MATRIX_START=$(date -Is)"
echo "CARLA_PORT=2000"
echo "EXPECTED_CELLS=6"
echo "EXPECTED_JOBS=510"
echo "BEST_RADAR=density"
echo "TRAINING_STARTED=NO"

if ! ss -ltn 2>/dev/null | grep -q ':2000 '; then
    echo "ERROR=CARLA_PORT_2000_NOT_LISTENING"
    exit 2
fi

if pgrep -af '[l]eaderboard_evaluator_parameter.py' >/dev/null 2>&1; then
    echo "ERROR=EVALUATOR_ALREADY_RUNNING"
    exit 3
fi

run_cell() {
    local cell="$1"
    local base_config="$2"

    echo
    echo "============================================================"
    echo "CELL_START=$cell"
    echo "BASE_CONFIG=$base_config"
    echo "============================================================"

    for part in 1s 2s 3s 4s 5s; do
        local log="${MATRIX_ROOT}/${cell}_${part}.log"

        echo "PART_START cell=${cell} part=${part} time=$(date -Is)"

        bash scripts/batch_eval_driving_e2e.sh \
            0 \
            2000 \
            "$cell" \
            0 \
            "$base_config" \
            "$part" \
            > "$log" 2>&1

        local rc=$?

        echo "PART_END cell=${cell} part=${part} rc=${rc} time=$(date -Is)"

        if [ "$rc" -ne 0 ]; then
            echo "PART_FAILED cell=${cell} part=${part} rc=${rc}"
        fi

        if ! ss -ltn 2>/dev/null | grep -q ':2000 '; then
            echo "ERROR=CARLA_DISAPPEARED_AFTER_${cell}_${part}"
            exit 4
        fi
    done

    echo "CELL_END=$cell time=$(date -Is)"
}

# Final protocol order:
# 1) Baseline vs Best Radar in OFF and RF3
# 2) Baseline vs Best Radar in RF2
run_cell \
    "stage9b_final_baseline_OFF" \
    "stage9b_baseline_seed2029_closed_loop_OFF"

run_cell \
    "stage9b_final_density_OFF" \
    "stage9b_density_seed2029_closed_loop_OFF"

run_cell \
    "stage9b_final_baseline_RF3" \
    "stage9b_baseline_seed2029_closed_loop_RF3"

run_cell \
    "stage9b_final_density_RF3" \
    "stage9b_density_seed2029_closed_loop_RF3"

run_cell \
    "stage9b_final_baseline_RF2" \
    "stage9b_baseline_seed2029_closed_loop_RF2"

run_cell \
    "stage9b_final_density_RF2" \
    "stage9b_density_seed2029_closed_loop_RF2"

echo
echo "FINAL_MATRIX_END=$(date -Is)"
echo "FINAL_MATRIX_FINISHED=YES"
echo "TRAINING_STARTED=NO"
