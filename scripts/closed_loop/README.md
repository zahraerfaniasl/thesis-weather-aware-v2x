# Closed-loop Evaluation Scripts

These scripts reproduce the final Stage-9b closed-loop evaluation matrix.

## Execution chain

```text
run_final_matrix.sh
└── run_route_part.sh
    └── run_single_route.sh
        └── leaderboard_evaluator_parameter.py
```

## Final matrix

The matrix contains six cells: baseline and density under OFF, RF2, and RF3.
Each cell runs five route parts containing 16, 18, 17, 18, and 16 routes.
This gives 85 route jobs per cell and 510 jobs across the complete matrix.

| Part | Route count | Configuration suffix |
|---|---:|---|
| 1s | 16 | 8_10 |
| 2s | 18 | 5_10 |
| 3s | 17 | 5_10 |
| 4s | 18 | 8_10 |
| 5s | 16 | 5_50 |

## Required environment

```bash
export V2XVERSE_ROOT=/path/to/V2Xverse
export CARLA_ROOT=/path/to/carla-0.9.10
```

Optional variables are PYTHON_BIN, CARLA_CLIENT_ROOT, and CARLA_EGG.
CARLA must already be listening on port 2000 before the matrix starts.

```bash
bash scripts/closed_loop/run_final_matrix.sh
```

## Provenance

The portable scripts preserve the execution logic of the three audited
upstream scripts. Only machine-specific paths and internal script references
were made portable. Original source hashes are recorded in
`SOURCE_CLOSED_LOOP_SHA256SUMS.txt`.

## Status and audit utilities



`check_matrix_status.sh` performs a lightweight matrix-controller audit. It verifies:



- all 30 cell/part log files;

- non-empty part logs;

- the controller log;

- the final matrix completion marker;

- the presence of all six result directories.



`audit_closed_loop_jobs.py` reconstructs the exact final protocol and validates:



- six final matrix cells;

- five route parts per cell;

- 85 expected jobs per cell;

- 510 expected jobs in total;

- top-level placeholder presence and JSON validity;
- substantive nested `ego_vehicle_*/results.json` records;
- clean and agent-error completion statuses;
- scenario-load exclusions and paired coverage across all six cells.



Example:



```bash

export V2XVERSE_ROOT=/path/to/V2Xverse

bash scripts/closed_loop/check_matrix_status.sh

python3 scripts/closed_loop/audit_closed_loop_jobs.py

```



The granular audit distinguishes the 510 top-level placeholder files from the 438 substantive nested route results.



## Provenance note



The three runner scripts are portable adaptations of the audited V2Xverse execution scripts listed in `SOURCE_CLOSED_LOOP_SHA256SUMS.txt`.



The status and job-audit utilities are repository-side reproducibility tools. They were created to validate the packaged final protocol and are not claimed to be the original historical execution scripts.

## Audited result semantics

Controller completion and top-level `results.json` presence do not by
themselves prove that a route produced a substantive evaluation result.
The top-level files are valid JSON placeholders. Substantive route records
are stored under:

```text
ego_vehicle_*/results.json
```

The granular audit of the historical final matrix established:

- 510 planned route jobs and 510 valid top-level placeholders;
- 438 substantive nested results, balanced at 73 per matrix cell;
- 356 routes with status `Finished`;
- 82 routes with status `Finished with agent errors`;
- 72 scenario-load exclusions before agent evaluation;
- zero unknown missing results and zero invalid nested JSON files.

The same 12 route-part combinations were excluded in every cell:

```text
1s:r8, 1s:r161,
2s:r7, 2s:r27, 2s:r161,
3s:r7, 3s:r8,
4s:r8, 4s:r160,
5s:r6, 5s:r7, 5s:r8
```

All 72 exclusions were traced to CARLA actor-spawn failures during
scenario loading: 70 involved `vehicle.diamondback.century` and two
involved `vehicle.volkswagen.t2`. The subsequent `Location` and
`route_length` errors were secondary effects of the failed scenario load.

The 82 agent-error records are substantive completed results and remain in
the evaluation dataset; their status is reported separately. Therefore the
final comparison uses a balanced paired subset of 438 substantive results.

The expected audit conclusion is:

```text
EVALUATION_COMPLETENESS=PARTIAL
PAIRED_SUBSTANTIVE_RESULTS=438
CLOSED_LOOP_RESULT_AUDIT=PASS_WITH_SCENARIO_LOAD_EXCLUSIONS
```
