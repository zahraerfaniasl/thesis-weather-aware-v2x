#!/usr/bin/env python
from __future__ import print_function

import csv
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(os.environ["V2XVERSE_ROOT"])
PIPELINE = ROOT / "results/stage9b_pipeline"
ENV_FILE = PIPELINE / "model_dirs.env"
OUTPUT = ROOT / "results/stage9b_final"
OUTPUT.mkdir(parents=True, exist_ok=True)


def load_shell_environment(path):
    command = (
        "set -a; source {}; env".format(
            subprocess.list2cmdline([str(path)])
        )
    )

    result = subprocess.check_output(
        ["bash", "-c", command],
        universal_newlines=True,
    )

    environment = {}

    for line in result.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            environment[key] = value

    return environment


def number(pattern, line):
    match = re.search(pattern, line, re.IGNORECASE)

    if not match:
        return ""

    try:
        return float(match.group(1))
    except Exception:
        return ""


def class_name(line):
    lower = line.lower()

    if "pedestrian" in lower:
        return "pedestrian"
    if "cyclist" in lower or "bicycle" in lower:
        return "bicycle"
    if "vehicle" in lower or " car " in lower:
        return "vehicle"
    if "average" in lower or "mean" in lower or "map" in lower:
        return "mean"

    return "unknown"


def test_type(path):
    lower = str(path).lower()

    if "latency" in lower:
        return "latency"
    if "noise" in lower or "pose" in lower:
        return "pose_noise"
    if "comm" in lower:
        return "communication"
    return "standard"


if not ENV_FILE.is_file():
    raise RuntimeError("Missing {}".format(ENV_FILE))

environment = load_shell_environment(ENV_FILE)

methods = {
    "baseline": environment.get(
        "STAGE9B_BASELINE_MODEL_DIR", ""
    ),
    "density": environment.get(
        "STAGE9B_DENSITY_MODEL_DIR", ""
    ),
    "density_doppler": environment.get(
        "STAGE9B_DENSITY_DOPPLER_MODEL_DIR", ""
    ),
    "density_doppler_gate": environment.get(
        "STAGE9B_DENSITY_DOPPLER_GATE_MODEL_DIR", ""
    ),
}

rows = []
raw_lines = []

ap30_pattern = (
    r"(?:AP\s*[@_:-]?\s*0?\.?30|AP30)"
    r"\s*[:=]?\s*([0-9]*\.?[0-9]+)"
)

ap50_pattern = (
    r"(?:AP\s*[@_:-]?\s*0?\.?50|AP50)"
    r"\s*[:=]?\s*([0-9]*\.?[0-9]+)"
)

ap70_pattern = (
    r"(?:AP\s*[@_:-]?\s*0?\.?70|AP70)"
    r"\s*[:=]?\s*([0-9]*\.?[0-9]+)"
)

comm_pattern = (
    r"(?:comm(?:unication)?[_ ]?rate)"
    r"\s*[:=]\s*([0-9]*\.?[0-9]+)"
)

for method, model_dir_text in methods.items():
    if not model_dir_text:
        continue

    model_dir = Path(model_dir_text)

    if not model_dir.is_dir():
        continue

    files = set()

    for pattern in ("*.txt", "*.log"):
        files.update(model_dir.rglob(pattern))

    for path in sorted(files):
        try:
            if path.stat().st_size > 20 * 1024 * 1024:
                continue

            text = path.read_text(
                errors="replace"
            )
        except Exception:
            continue

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            lower = line.lower()

            if not any(token in lower for token in (
                "ap30",
                "ap50",
                "ap70",
                "ap@",
                "comm_rate",
                "communication_rate",
                "latency:",
                "pos_std:",
            )):
                continue

            ap30 = number(ap30_pattern, line)
            ap50 = number(ap50_pattern, line)
            ap70 = number(ap70_pattern, line)
            comm_rate = number(comm_pattern, line)

            raw_lines.append({
                "method": method,
                "test": test_type(path),
                "source": str(path),
                "line_number": line_number,
                "line": line.strip(),
            })

            if (
                ap30 != ""
                or ap50 != ""
                or ap70 != ""
                or comm_rate != ""
            ):
                rows.append({
                    "method": method,
                    "test": test_type(path),
                    "class": class_name(line),
                    "ap30": ap30,
                    "ap50": ap50,
                    "ap70": ap70,
                    "communication_rate": comm_rate,
                    "source": str(path),
                    "line_number": line_number,
                })

metric_path = OUTPUT / "openloop_metrics.tsv"
raw_path = OUTPUT / "openloop_metric_lines.tsv"

metric_fields = (
    "method",
    "test",
    "class",
    "ap30",
    "ap50",
    "ap70",
    "communication_rate",
    "source",
    "line_number",
)

with metric_path.open("w", newline="") as stream:
    writer = csv.DictWriter(
        stream,
        delimiter="\t",
        fieldnames=metric_fields,
    )
    writer.writeheader()
    writer.writerows(rows)

raw_fields = (
    "method",
    "test",
    "source",
    "line_number",
    "line",
)

with raw_path.open("w", newline="") as stream:
    writer = csv.DictWriter(
        stream,
        delimiter="\t",
        fieldnames=raw_fields,
    )
    writer.writeheader()
    writer.writerows(raw_lines)

marker = PIPELINE / "markers/34_openloop_metrics_complete"
marker.write_text(
    "completed_at={}\nrows={}\n".format(
        subprocess.check_output(
            ["date", "-Is"],
            universal_newlines=True,
        ).strip(),
        len(rows),
    )
)

print("METRIC_ROWS={}".format(len(rows)))
print("RAW_METRIC_LINES={}".format(len(raw_lines)))
print("METRICS={}".format(metric_path))
print("RAW_LINES={}".format(raw_path))

if raw_lines:
    print("OPENLOOP_METRIC_COLLECTION=PASS")
else:
    print("OPENLOOP_METRIC_COLLECTION=CHECK")

# STAGE9B_GATE_PIPELINE_PATCH
