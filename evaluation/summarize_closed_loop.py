#!/usr/bin/env python3
"""Summarize the Stage-9b closed-loop results and compare the two methods.

Reads every ``ego_vehicle_0/results.json`` below the result directories
``results_driving_stage9b_final_<method>_<weather>`` and writes:

- ``closed_loop_jobs.csv``: one row per counted job;
- ``closed_loop_cells.csv``: one row per method and weather condition;
- ``closed_loop_paired_bootstrap.csv``: Density minus Baseline per weather.

A job is counted only when it has an ego-level record. The bootstrap
resamples jobs, not unique route IDs. Python 3.7 compatible; standard
library only.

Usage:
    python summarize_closed_loop.py --results-root RESULTS --output-dir OUT
"""
import argparse
import csv
import glob
import json
import os
import random
import statistics

METHODS = ("baseline", "density")
WEATHERS = ("OFF", "RF2", "RF3")
COLLISIONS = (
    "collisions_pedestrian",
    "collisions_vehicle",
    "collisions_layout",
)
OTHER_INFRACTIONS = ("vehicle_blocked", "stop_infraction", "outside_route_lanes")
BOOTSTRAP_ITERATIONS = 5000
BOOTSTRAP_SEED = 2029


def cell_pattern(root, method, weather):
    return os.path.join(
        glob.escape(root),
        "results_driving_stage9b_final_{}_{}".format(method, weather),
        "v2x_final",
        "town05_short_collab",
        "*",
    )


def load_cell(root, method, weather):
    """Return counted jobs and the number of jobs without an ego record."""
    jobs = {}
    excluded = 0
    for job_dir in sorted(glob.glob(cell_pattern(root, method, weather))):
        job = os.path.basename(job_dir)
        path = os.path.join(job_dir, "ego_vehicle_0", "results.json")
        records = []
        if os.path.isfile(path):
            with open(path) as handle:
                records = json.load(handle).get("_checkpoint", {}).get("records", [])
        if not records:
            excluded += 1
            continue
        record = records[-1]
        infractions = record.get("infractions", {})
        row = {
            "method": method,
            "weather": weather,
            "job": job,
            "driving_score": record["scores"]["score_composed"],
            "route_completion": record["scores"]["score_route"],
            "status": record.get("status", ""),
        }
        for name in COLLISIONS + OTHER_INFRACTIONS:
            row[name] = len(infractions.get(name, []))
        jobs[job] = row
    return jobs, excluded


def write_csv(path, rows):
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize_cell(method, weather, jobs, excluded):
    rows = list(jobs.values())
    row = {
        "method": method,
        "weather": weather,
        "counted_jobs": len(rows),
        "excluded_jobs": excluded,
        "driving_score_mean": round(
            statistics.mean(r["driving_score"] for r in rows), 2
        ),
        "route_completion_mean": round(
            statistics.mean(r["route_completion"] for r in rows), 2
        ),
    }
    for name in COLLISIONS + OTHER_INFRACTIONS:
        row[name] = sum(r[name] for r in rows)
    row["collisions_total"] = sum(row[name] for name in COLLISIONS)
    return row


def paired_bootstrap(differences, rng):
    means = sorted(
        statistics.mean(rng.choices(differences, k=len(differences)))
        for _ in range(BOOTSTRAP_ITERATIONS)
    )
    low = means[int(0.025 * BOOTSTRAP_ITERATIONS)]
    high = means[int(0.975 * BOOTSTRAP_ITERATIONS) - 1]
    return statistics.mean(differences), low, high


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)

    cells = {}
    job_rows = []
    cell_rows = []
    for method in METHODS:
        for weather in WEATHERS:
            jobs, excluded = load_cell(args.results_root, method, weather)
            if not jobs:
                raise SystemExit(
                    "No counted jobs for {} {}".format(method, weather)
                )
            cells[(method, weather)] = jobs
            job_rows.extend(jobs.values())
            cell_rows.append(summarize_cell(method, weather, jobs, excluded))

    rng = random.Random(BOOTSTRAP_SEED)
    paired_rows = []
    for weather in WEATHERS:
        baseline = cells[("baseline", weather)]
        density = cells[("density", weather)]
        shared = sorted(set(baseline) & set(density))
        for metric in ("driving_score", "route_completion"):
            differences = [
                density[job][metric] - baseline[job][metric] for job in shared
            ]
            mean, low, high = paired_bootstrap(differences, rng)
            paired_rows.append(
                {
                    "weather": weather,
                    "metric": metric,
                    "paired_jobs": len(shared),
                    "density_minus_baseline": round(mean, 2),
                    "ci95_low": round(low, 2),
                    "ci95_high": round(high, 2),
                    "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
                    "bootstrap_seed": BOOTSTRAP_SEED,
                }
            )

    write_csv(os.path.join(args.output_dir, "closed_loop_jobs.csv"), job_rows)
    write_csv(os.path.join(args.output_dir, "closed_loop_cells.csv"), cell_rows)
    write_csv(
        os.path.join(args.output_dir, "closed_loop_paired_bootstrap.csv"),
        paired_rows,
    )


if __name__ == "__main__":
    main()
