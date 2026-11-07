# Results

Small result tables from the Stage-9b experiments. Raw logs, datasets, and
checkpoints are not included.

Read `README.md` in the repository root first. The closed-loop tables do not
measure the effect of radar, because the radar input was all zeros.

## Files

| File | Contents | Models | Data |
|---|---|---|---|
| `offline/screening_town04_val_matrix.csv` | mAP and per-class AP, 4 methods x 4 weather conditions | `stage9b_clean_*_pilot` | Town04 validation, 6 routes |
| `offline/screening_route_bootstrap.csv` | Route-level bootstrap, Baseline vs Density | `stage9b_clean_*_pilot` | Town04 validation, 6 routes |
| `offline/town05_test_confirm3.csv` | mAP and per-class AP, OFF and RF3 | `confirm3` `net_epoch3.pth` | Town05 subset, 7 routes |
| `closed_loop/closed_loop_cells.csv` | Scores and infractions per method and weather | `confirm3` `net_epoch_bestval_at1.pth` | Town05 |
| `closed_loop/closed_loop_paired_bootstrap.csv` | Density minus Baseline, with 95% CI | same | Town05 |
| `closed_loop/closed_loop_jobs.csv` | One row per counted job | same | Town05 |

Class IDs in the offline tables: 0 Vehicle, 1 Pedestrian, 3 Bicycle.

## How to read them

- The three offline and closed-loop model sets are different, so numbers
  cannot be compared directly across these groups.
- All offline numbers use small route samples and one model per method.
- `closed_loop_*.csv` count 73 of 85 jobs per cell. The same 12 jobs have no
  ego-level result record in all six cells.
- The closed-loop bootstrap resamples jobs, not unique routes. Some routes
  appear in several jobs, so the intervals may be slightly too narrow.

## Regenerating the closed-loop tables

```bash
python evaluation/summarize_closed_loop.py --results-root RESULTS_DIR --output-dir results/closed_loop
```
