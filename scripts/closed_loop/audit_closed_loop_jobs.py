#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

CELLS = (
    "stage9b_final_baseline_OFF",
    "stage9b_final_baseline_RF2",
    "stage9b_final_baseline_RF3",
    "stage9b_final_density_OFF",
    "stage9b_final_density_RF2",
    "stage9b_final_density_RF3",
)

PARTS = (
    ("1s", "0_1_8_10", (2, 3, 5, 8, 10, 13, 18, 31, 135, 146, 147, 161, 300, 310, 326, 327)),
    ("2s", "0_2_5_10", (2, 3, 7, 12, 19, 22, 24, 25, 27, 136, 138, 161, 300, 320, 321, 322, 328, 329)),
    ("3s", "0_3_5_10", (7, 8, 16, 31, 300, 301, 305, 310, 311, 313, 314, 316, 320, 324, 329, 330, 331)),
    ("4s", "0_4_8_10", (1, 8, 9, 12, 14, 15, 16, 28, 140, 145, 160, 311, 312, 317, 321, 323, 328, 331)),
    ("5s", "0_5_5_50", (1, 6, 7, 8, 18, 20, 28, 31, 142, 145, 146, 157, 306, 310, 315, 318)),
)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Audit substantive Stage-9b closed-loop results."
    )
    parser.add_argument(
        "--v2xverse-root",
        default=os.environ.get("V2XVERSE_ROOT"),
        help="V2Xverse root; defaults to V2XVERSE_ROOT.",
    )
    return parser.parse_args()

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)

def is_substantive(data):
    if not isinstance(data, dict):
        return False
    checkpoint = data.get("_checkpoint") or {}
    return bool(
        checkpoint.get("records")
        or checkpoint.get("global_record")
        or data.get("values")
        or data.get("entry_status")
    )

def job_directory(results_root, cell, route, suffix):
    return (
        results_root
        / ("results_driving_" + cell)
        / "v2x_final"
        / "town05_short_collab"
        / ("r{}_repeat{}".format(route, suffix))
    )

def route_blocks(log_path):
    if not log_path.is_file():
        return {}
    lines = log_path.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    markers = []
    for index, line in enumerate(lines):
        match = re.match(r"^\s*route_idx\s+(\d+)\s*$", line)
        if match:
            markers.append((index, int(match.group(1))))
    collected = {}
    for marker_index, item in enumerate(markers):
        start, route = item
        if marker_index + 1 < len(markers):
            end = markers[marker_index + 1][0]
        else:
            end = len(lines)
        collected.setdefault(route, []).append(
            "\n".join(lines[start:end])
        )
    return {
        route: "\n".join(blocks)
        for route, blocks in collected.items()
    }

def main():
    args = parse_args()
    if not args.v2xverse_root:
        print("ERROR: set V2XVERSE_ROOT or use --v2xverse-root.")
        return 2
    root = Path(args.v2xverse_root).expanduser().resolve()
    results_root = root / "results"
    matrix_root = results_root / "stage9b_final_matrix_20260917"
    if not results_root.is_dir():
        print("ERROR: results directory not found: {}".format(results_root))
        return 2
    routes_per_cell = sum(len(routes) for _, _, routes in PARTS)
    expected_total = len(CELLS) * routes_per_cell
    if routes_per_cell != 85 or expected_total != 510:
        print("ERROR: internal matrix definition is inconsistent.")
        return 2
    totals = Counter()
    statuses = Counter()
    actors = Counter()
    missing_patterns = {}
    substantive_per_cell = []
    print("=== GRANULAR CLOSED-LOOP RESULT AUDIT ===")
    print("v2xverse_root={}".format(root))
    print("planned_jobs={}".format(expected_total))
    for cell in CELLS:
        counts = Counter()
        cell_statuses = Counter()
        missing = []
        blocks_by_part = {}
        for part, _, _ in PARTS:
            blocks_by_part[part] = route_blocks(
                matrix_root / ("{}_{}.log".format(cell, part))
            )
        for part, suffix, routes in PARTS:
            for route in routes:
                counts["expected"] += 1
                job_dir = job_directory(
                    results_root, cell, route, suffix
                )
                placeholder = job_dir / "results.json"
                if placeholder.is_file():
                    counts["placeholder_present"] += 1
                    _, error = read_json(placeholder)
                    if error is None:
                        counts["placeholder_valid"] += 1
                    else:
                        counts["placeholder_invalid"] += 1
                selected = None
                for nested in sorted(
                    job_dir.glob("ego_vehicle_*/results.json")
                ):
                    data, error = read_json(nested)
                    if error is not None:
                        counts["nested_invalid"] += 1
                        continue
                    if is_substantive(data):
                        selected = data
                        break
                if selected is not None:
                    counts["substantive"] += 1
                    checkpoint = selected.get("_checkpoint") or {}
                    status = str(selected.get("entry_status") or "")
                    statuses[status or "<empty>"] += 1
                    cell_statuses[status or "<empty>"] += 1
                    if checkpoint.get("progress") == [1, 1]:
                        counts["progress_complete"] += 1
                    if status == "Finished":
                        counts["finished_clean"] += 1
                    elif "agent errors" in status.lower():
                        counts["finished_agent_errors"] += 1
                    else:
                        counts["other_status"] += 1
                    continue
                counts["missing_substantive"] += 1
                missing.append("{}:r{}".format(part, route))
                block = blocks_by_part.get(part, {}).get(route, "")
                actor_matches = re.findall(
                    r"Unable to spawn vehicle\s+(vehicle\.[A-Za-z0-9_.-]+)",
                    block,
                )
                scenario_failure = bool(
                    actor_matches
                    and "route_length" in block
                    and "object is not iterable" in block
                )
                if scenario_failure:
                    counts["scenario_load_failure"] += 1
                    actors[actor_matches[0]] += 1
                else:
                    counts["unknown_missing"] += 1
        totals.update(counts)
        missing_patterns[cell] = tuple(missing)
        substantive_per_cell.append(counts["substantive"])
        print(
            "CELL={} expected={} substantive={} clean={} agent_errors={} scenario_failures={} unknown_missing={}".format(
                cell,
                counts["expected"],
                counts["substantive"],
                counts["finished_clean"],
                counts["finished_agent_errors"],
                counts["scenario_load_failure"],
                counts["unknown_missing"],
            )
        )
    patterns = set(missing_patterns.values())
    same_pattern = len(patterns) == 1
    balanced = len(set(substantive_per_cell)) == 1
    print()
    print("=== TOTALS ===")
    for key in (
        "expected",
        "placeholder_present",
        "placeholder_valid",
        "placeholder_invalid",
        "substantive",
        "progress_complete",
        "finished_clean",
        "finished_agent_errors",
        "other_status",
        "missing_substantive",
        "scenario_load_failure",
        "unknown_missing",
        "nested_invalid",
    ):
        print("{}={}".format(key, totals[key]))
    print("status_distribution={}".format(dict(statuses)))
    print("spawn_actor_distribution={}".format(dict(actors)))
    print("all_cells_same_missing_pattern={}".format(same_pattern))
    print("balanced_substantive_results={}".format(balanced))
    if same_pattern:
        shared = next(iter(patterns))
        print("shared_scenario_exclusions={}".format(len(shared)))
        print("shared_exclusion_list={}".format(", ".join(shared)))
    passed = all((
        totals["expected"] == 510,
        totals["placeholder_present"] == 510,
        totals["placeholder_valid"] == 510,
        totals["placeholder_invalid"] == 0,
        totals["substantive"] == 438,
        totals["progress_complete"] == 438,
        totals["finished_clean"] == 356,
        totals["finished_agent_errors"] == 82,
        totals["other_status"] == 0,
        totals["scenario_load_failure"] == 72,
        totals["unknown_missing"] == 0,
        totals["nested_invalid"] == 0,
        actors["vehicle.diamondback.century"] == 70,
        actors["vehicle.volkswagen.t2"] == 2,
        same_pattern,
        balanced,
    ))
    print()
    print("EVALUATION_COMPLETENESS=PARTIAL")
    print("PAIRED_SUBSTANTIVE_RESULTS={}".format(totals["substantive"]))
    if passed:
        print("CLOSED_LOOP_RESULT_AUDIT=PASS_WITH_SCENARIO_LOAD_EXCLUSIONS")
        return 0
    print("CLOSED_LOOP_RESULT_AUDIT=REVIEW")
    return 1

if __name__ == "__main__":
    sys.exit(main())
