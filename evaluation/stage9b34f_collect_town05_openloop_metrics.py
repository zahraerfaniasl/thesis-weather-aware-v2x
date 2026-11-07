#!/usr/bin/env python
import os
from __future__ import print_function

import argparse
import csv
import json
from pathlib import Path

import yaml


ROOT = Path(os.environ["V2XVERSE_ROOT"])

VIEWS = ROOT / (
    "results/stage9b_pipeline/town05_test_views"
)

OUTPUT = ROOT / "results/stage9b_final"
OUTPUT.mkdir(parents=True, exist_ok=True)

METHODS = (
    "baseline",
    "density",
    "density_doppler",
    "density_doppler_gate",
)

WEATHERS = (
    "clear",
    "moderate",
    "severe",
)

CLASS_NAMES = {
    0: "vehicle",
    1: "pedestrian",
    3: "bicycle",
}

FIELDS = (
    "split",
    "town",
    "weather",
    "method",
    "class_id",
    "class",
    "ap30",
    "ap50",
    "ap70",
    "source",
)


def atomic_write_tsv(path, rows):
    temporary = path.with_name(
        ".{}.tmp".format(path.name)
    )

    with temporary.open("w") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(FIELDS),
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    temporary.replace(path)


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def class_result(results, class_id):
    candidates = (
        class_id,
        str(class_id),
        "class_{}".format(class_id),
    )

    for key in candidates:
        value = results.get(key)

        if isinstance(value, dict):
            return value

    return None


def expected_eval_path(view, weather, method):
    name = (
        "eval_intermediate_stage9b_town05_"
        "{}_{}.yaml".format(weather, method)
    )

    exact = view / name

    if exact.is_file():
        return exact

    candidates = sorted(
        view.glob(
            "eval_*town05*{}*{}*.yaml".format(
                weather,
                method,
            )
        ),
        key=lambda path: (
            path.stat().st_mtime,
            path.name,
        ),
    )

    if candidates:
        return candidates[-1]

    # Fallback for manually executed inference.
    generic = sorted(
        view.glob("eval_*.yaml"),
        key=lambda path: (
            path.stat().st_mtime,
            path.name,
        ),
    )

    return generic[-1] if generic else None


def inspect_inputs():
    view_configs = 0
    evaluation_files = 0
    route_stat_files = 0
    missing = []

    for weather in WEATHERS:
        for method in METHODS:
            view = VIEWS / weather / method

            if (view / "config.yaml").is_file():
                view_configs += 1

            evaluation = expected_eval_path(
                view,
                weather,
                method,
            )

            if evaluation is not None:
                evaluation_files += 1
            else:
                missing.append(
                    "{}:{}".format(weather, method)
                )

            if (
                view / "route_detection_stats.json"
            ).is_file():
                route_stat_files += 1

    print("TOWN05_VIEW_CONFIGS={}/12".format(
        view_configs
    ))
    print("TOWN05_EVAL_FILES={}/12".format(
        evaluation_files
    ))
    print("TOWN05_ROUTE_STATS={}/12".format(
        route_stat_files
    ))

    if missing:
        print("MISSING_EVALUATIONS={}".format(
            ",".join(missing)
        ))

    ready = (
        view_configs == 12
        and evaluation_files == 12
    )

    return ready, route_stat_files


def collect_metrics():
    rows = []
    sources = []

    for weather in WEATHERS:
        for method in METHODS:
            view = VIEWS / weather / method

            evaluation = expected_eval_path(
                view,
                weather,
                method,
            )

            if evaluation is None:
                raise RuntimeError(
                    "Evaluation result missing: "
                    "{} {}".format(weather, method)
                )

            with evaluation.open() as stream:
                results = yaml.safe_load(stream) or {}

            method_rows = []

            for class_id in (0, 1, 3):
                metrics = class_result(
                    results,
                    class_id,
                )

                if metrics is None:
                    raise RuntimeError(
                        "Class {} missing from {}".format(
                            class_id,
                            evaluation,
                        )
                    )

                row = {
                    "split": "test",
                    "town": "05",
                    "weather": weather,
                    "method": method,
                    "class_id": class_id,
                    "class": CLASS_NAMES[class_id],
                    "ap30": to_float(
                        metrics.get("ap30")
                    ),
                    "ap50": to_float(
                        metrics.get("ap50")
                    ),
                    "ap70": to_float(
                        metrics.get("ap70")
                    ),
                    "source": str(evaluation),
                }

                rows.append(row)
                method_rows.append(row)

            # Macro average over Vehicle, Pedestrian and Bicycle.
            rows.append({
                "split": "test",
                "town": "05",
                "weather": weather,
                "method": method,
                "class_id": "all",
                "class": "mAP",
                "ap30": sum(
                    row["ap30"] for row in method_rows
                ) / len(method_rows),
                "ap50": sum(
                    row["ap50"] for row in method_rows
                ) / len(method_rows),
                "ap70": sum(
                    row["ap70"] for row in method_rows
                ) / len(method_rows),
                "source": str(evaluation),
            })

            sources.append({
                "weather": weather,
                "method": method,
                "evaluation": str(evaluation),
                "route_detection_stats": str(
                    view /
                    "route_detection_stats.json"
                ),
            })

    if len(rows) != 48:
        raise RuntimeError(
            "Expected 48 metric rows, got {}".format(
                len(rows)
            )
        )

    metric_path = (
        OUTPUT / "town05_openloop_metrics.tsv"
    )

    atomic_write_tsv(metric_path, rows)

    manifest_path = (
        OUTPUT / "town05_openloop_manifest.json"
    )

    manifest = {
        "split": "test",
        "town": 5,
        "methods": list(METHODS),
        "weathers": list(WEATHERS),
        "metric_rows": len(rows),
        "evaluations": sources,
        "metrics": str(metric_path),
    }

    temporary = manifest_path.with_name(
        ".{}.tmp".format(manifest_path.name)
    )

    temporary.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
    )
    temporary.replace(manifest_path)

    print("TOWN05_METRIC_ROWS={}".format(
        len(rows)
    ))
    print("TOWN05_METRICS={}".format(metric_path))
    print("TOWN05_MANIFEST={}".format(
        manifest_path
    ))
    print("TOWN05_OPENLOOP_METRICS=PASS")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Collect final Town05 Open-loop metrics."
        )
    )

    parser.add_argument(
        "mode",
        nargs="?",
        choices=("check", "collect"),
        default="check",
    )

    args = parser.parse_args()

    ready, route_stats = inspect_inputs()

    if args.mode == "check":
        if ready:
            print("TOWN05_METRIC_INPUTS=READY")
        else:
            print(
                "TOWN05_METRIC_INPUTS="
                "WAITING_FOR_INFERENCE"
            )

        if route_stats == 12:
            print("TOWN05_BOOTSTRAP_INPUTS=READY")
        else:
            print(
                "TOWN05_BOOTSTRAP_INPUTS="
                "WAITING_FOR_INFERENCE"
            )

        print("TOWN05_METRIC_CHECK=PASS")
        return

    if not ready:
        raise RuntimeError(
            "Town05 inference results are incomplete."
        )

    if route_stats != 12:
        raise RuntimeError(
            "Town05 route-level statistics are incomplete: "
            "{}/12".format(route_stats)
        )

    collect_metrics()


if __name__ == "__main__":
    main()
