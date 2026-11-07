#!/usr/bin/env python3
import argparse
import csv
import os
import re
import sys
from pathlib import Path

import yaml

METHODS = (
    "baseline",
    "density",
    "density_doppler",
    "density_doppler_gate",
)

WEATHERS = ("OFF", "RF1", "RF2", "RF3")

CLASSES = (
    (3, "Vehicle"),
    (1, "Pedestrian"),
    (0, "Bicycle"),
)

IOU_METRICS = ("ap30", "ap50", "ap70")
FIXED_THRESHOLD = 0.20

SCORE_PATTERN = re.compile(
    r"^\s*score_threshold\s*:\s*[\"']?([0-9.eE+-]+)",
    re.MULTILINE,
)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract fixed-confidence metrics from the 16-cell offline matrix."
    )
    parser.add_argument(
        "--view-root",
        default=os.environ.get("OFFLINE_VIEW_ROOT"),
        help="Root containing WEATHER/METHOD model views.",
    )
    parser.add_argument(
        "--output",
        help="Output TSV path; defaults to VIEW_ROOT/fixed_confidence_metrics.tsv.",
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=FIXED_THRESHOLD,
        help="Required confidence threshold; only 0.20 is supported.",
    )
    parser.add_argument(
        "--show-problems",
        type=int,
        default=20,
        help="Maximum number of problems to print.",
    )
    return parser.parse_args()

def verify_threshold(config_path, expected):
    if not config_path.is_file():
        raise ValueError("config.yaml is missing")

    text = config_path.read_text(encoding="utf-8", errors="replace")
    values = [float(value) for value in SCORE_PATTERN.findall(text)]

    if not values:
        raise ValueError("score_threshold was not found in config.yaml")

    if not any(abs(value - expected) < 1e-9 for value in values):
        raise ValueError(
            "score_threshold mismatch: found {}".format(values)
        )

def get_class_block(data, class_id):
    for key in (class_id, str(class_id)):
        if key in data:
            block = data[key]
            if not isinstance(block, dict):
                raise ValueError("class {} block is not a mapping".format(class_id))
            return block

    raise ValueError("class {} is missing".format(class_id))

def get_metric(block, metric):
    if metric not in block:
        raise ValueError("{} is missing".format(metric))

    value = block[metric]

    if isinstance(value, list):
        if len(value) != 1:
            raise ValueError(
                "{} must contain exactly one value; found {}".format(
                    metric, len(value)
                )
            )
        value = value[0]

    return float(value)

def main():
    args = parse_args()

    if not args.view_root:
        print("ERROR: provide --view-root or set OFFLINE_VIEW_ROOT.")
        return 2

    if abs(args.score_threshold - FIXED_THRESHOLD) >= 1e-9:
        print("ERROR: this extractor only supports score threshold 0.20.")
        return 2

    view_root = Path(args.view_root).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else view_root / "fixed_confidence_metrics.tsv"
    )

    rows = []
    problems = []

    for weather in WEATHERS:
        for method in METHODS:
            model_dir = view_root / weather / method
            config_path = model_dir / "config.yaml"
            ap_path = model_dir / "AP030507.yaml"

            try:
                verify_threshold(config_path, args.score_threshold)

                if not ap_path.is_file():
                    raise ValueError("AP030507.yaml is missing")

                with ap_path.open("r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle)

                if not isinstance(data, dict):
                    raise ValueError("AP030507.yaml is not a mapping")

                for class_id, class_name in CLASSES:
                    block = get_class_block(data, class_id)
                    metrics = {
                        metric: get_metric(block, metric)
                        for metric in IOU_METRICS
                    }

                    rows.append({
                        "weather": weather,
                        "method": method,
                        "confidence_threshold": "{:.2f}".format(args.score_threshold),
                        "class_id": class_id,
                        "class_name": class_name,
                        "ap30": metrics["ap30"],
                        "ap50": metrics["ap50"],
                        "ap70": metrics["ap70"],
                        "source": str(ap_path),
                    })

            except (OSError, ValueError, yaml.YAMLError) as exc:
                problems.append((weather, method, str(exc)))

    print("=== FIXED-CONFIDENCE METRIC EXTRACTION ===")
    print("view_root={}".format(view_root))
    print("expected_cells=16")
    print("expected_rows=48")
    print("score_threshold={:.2f}".format(args.score_threshold))
    print("extracted_rows={}".format(len(rows)))
    print("problem_cells={}".format(len(problems)))

    if problems:
        limit = max(args.show_problems, 0)
        for weather, method, error in problems[:limit]:
            print(
                "PROBLEM weather={} method={} error={}".format(
                    weather, method, error
                )
            )

        print()
        print("FIXED_CONFIDENCE_EXTRACTION=INCOMPLETE")
        return 1

    if len(rows) != 48:
        print("ERROR: expected 48 metric rows; found {}.".format(len(rows)))
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)

    fields = (
        "weather",
        "method",
        "confidence_threshold",
        "class_id",
        "class_name",
        "ap30",
        "ap50",
        "ap70",
        "source",
    )

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print("output={}".format(output))
    print("FIXED_CONFIDENCE_EXTRACTION=PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
