#!/usr/bin/env python
import os
from __future__ import print_function

import csv
import json
import re
from pathlib import Path


ROOT = Path(os.environ["V2XVERSE_ROOT"])
RESULTS = ROOT / "results"
OUTPUT = RESULTS / "stage9b_final"
OUTPUT.mkdir(parents=True, exist_ok=True)

rows = []


def count_infractions(infractions, key):
    value = infractions.get(key, [])

    if isinstance(value, list):
        return len(value)

    if isinstance(value, (int, float)):
        return int(value)

    return 0


for experiment in sorted(
    RESULTS.glob("stage9b_*_*")
):
    if not experiment.is_dir():
        continue

    match = re.match(
        r"stage9b_"
        r"(baseline|density|density_doppler|density_doppler_gate)_"
        r"(preflight|scenario3|paper)$",
        experiment.name,
    )

    if not match:
        continue

    method, mode = match.groups()

    for result_file in sorted(
        experiment.glob("route_*_scen*/results.json")
    ):
        route_match = re.search(
            r"route_(\d+)_scen_?(\d+)",
            str(result_file.parent.name),
        )

        route_id = ""
        part = ""

        if route_match:
            route_id = route_match.group(1)
            part = route_match.group(2)

        try:
            content = json.loads(
                result_file.read_text()
            )
        except Exception:
            continue

        checkpoint = content.get("_checkpoint", {})
        records = checkpoint.get("records", [])

        if not records:
            records = content.get("records", [])

        for record_index, record in enumerate(records):
            scores = record.get("scores", {})
            infractions = record.get("infractions", {})
            meta = record.get("meta", {})

            ds = scores.get("score_composed", "")
            rc = scores.get("score_route", "")
            infraction_score = scores.get(
                "score_penalty", ""
            )

            collision_pedestrian = count_infractions(
                infractions,
                "collisions_pedestrian",
            )

            collision_vehicle = count_infractions(
                infractions,
                "collisions_vehicle",
            )

            collision_layout = count_infractions(
                infractions,
                "collisions_layout",
            )

            duration_game = meta.get(
                "duration_game", 0
            ) or 0

            route_length = meta.get(
                "route_length", 0
            ) or 0

            average_velocity_kmh = ""

            if duration_game and route_length:
                average_velocity_kmh = (
                    float(route_length) /
                    float(duration_game) *
                    3.6
                )

            rows.append({
                "method": method,
                "mode": mode,
                "part": part,
                "route": route_id,
                "record": record_index,
                "status": record.get("status", ""),
                "ds": ds,
                "rc": rc,
                "is": infraction_score,
                "collision_pedestrian":
                    collision_pedestrian,
                "collision_vehicle":
                    collision_vehicle,
                "collision_layout":
                    collision_layout,
                "collision_total": (
                    collision_pedestrian +
                    collision_vehicle +
                    collision_layout
                ),
                "average_velocity_kmh":
                    average_velocity_kmh,
                "duration_game_s": duration_game,
                "route_length_m": route_length,
                "result_file": str(result_file),
            })

output = OUTPUT / "closedloop_metrics.tsv"

fields = (
    "method",
    "mode",
    "part",
    "route",
    "record",
    "status",
    "ds",
    "rc",
    "is",
    "collision_pedestrian",
    "collision_vehicle",
    "collision_layout",
    "collision_total",
    "average_velocity_kmh",
    "duration_game_s",
    "route_length_m",
    "result_file",
)

with output.open("w", newline="") as stream:
    writer = csv.DictWriter(
        stream,
        delimiter="\t",
        fieldnames=fields,
    )
    writer.writeheader()
    writer.writerows(rows)

print("CLOSEDLOOP_ROWS={}".format(len(rows)))
print("OUTPUT={}".format(output))
print("CLOSEDLOOP_METRIC_COLLECTION=PASS")

# STAGE9B_GATE_PIPELINE_PATCH
