#!/usr/bin/env python
from __future__ import print_function

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from opencood.utils import eval_utils


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

CLASS_IDS = (0, 1, 3)

CLASS_NAMES = {
    0: "vehicle",
    1: "pedestrian",
    3: "bicycle",
}

IOU_THRESHOLDS = (0.3, 0.5, 0.7)


def load_routes(path):
    payload = json.loads(path.read_text())

    if "routes" not in payload:
        raise RuntimeError(
            "Invalid statistics file: {}".format(path)
        )

    return payload["routes"]


def empty_stat():
    return {
        "tp": [],
        "fp": [],
        "score": [],
        "gt": 0,
    }


def route_stat(route_data, class_id, iou):
    class_data = route_data.get(
        str(class_id),
        route_data.get(class_id, {}),
    )

    iou_key = str(iou)

    if iou_key not in class_data:
        iou_key = "{:.1f}".format(iou)

    return class_data.get(iou_key, empty_stat())


def aggregate(
        routes,
        sampled_route_names,
        class_id,
        iou):

    result = empty_stat()

    for route_name in sampled_route_names:
        current = route_stat(
            routes[route_name],
            class_id,
            iou,
        )

        result["tp"].extend(current.get("tp", []))
        result["fp"].extend(current.get("fp", []))
        result["score"].extend(
            current.get("score", [])
        )
        result["gt"] += int(current.get("gt", 0))

    return result


def calculate_ap(routes, sampled, class_id, iou):
    merged = aggregate(
        routes,
        sampled,
        class_id,
        iou,
    )

    if merged["gt"] <= 0:
        return float("nan")

    holder = {float(iou): merged}

    ap, _, _ = eval_utils.calculate_ap(
        holder,
        float(iou),
    )

    return float(ap)


def percentile(values, q):
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]

    if values.size == 0:
        return float("nan")

    return float(np.percentile(values, q))


def write_tsv(path, rows):
    if not rows:
        raise RuntimeError(
            "No output rows generated"
        )

    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            delimiter="\t",
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--root",
        default=(
            "results/stage9b_pipeline/"
            "weather_eval_views"
        ),
    )

    parser.add_argument(
        "--output",
        default="results/stage9b_final",
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
    )

    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    rng = np.random.RandomState(args.seed)

    summary_rows = []
    delta_rows = []
    manifest_rows = []

    for weather in WEATHERS:
        method_routes = {}

        for method in METHODS:
            path = (
                root / weather / method /
                "route_detection_stats.json"
            )

            if not path.is_file():
                print("MISSING={}".format(path))
                continue

            method_routes[method] = load_routes(path)

        if "baseline" not in method_routes:
            print(
                "SKIP_WEATHER={} REASON=BASELINE_MISSING".format(
                    weather
                )
            )
            continue

        available_methods = [
            method for method in METHODS
            if method in method_routes
        ]

        common_routes = set(
            method_routes["baseline"].keys()
        )

        for method in available_methods[1:]:
            common_routes &= set(
                method_routes[method].keys()
            )

        common_routes = sorted(common_routes)

        if not common_routes:
            print(
                "SKIP_WEATHER={} REASON=NO_COMMON_ROUTES".format(
                    weather
                )
            )
            continue

        manifest_rows.append({
            "weather": weather,
            "methods": ",".join(available_methods),
            "common_routes": len(common_routes),
            "bootstrap_iterations": args.iterations,
            "seed": args.seed,
        })

        bootstrap_samples = []

        for _ in range(args.iterations):
            indices = rng.randint(
                0,
                len(common_routes),
                size=len(common_routes),
            )

            bootstrap_samples.append([
                common_routes[int(index)]
                for index in indices
            ])

        ap_samples = {}

        for method in available_methods:
            for iou in IOU_THRESHOLDS:
                class_point_values = []
                class_bootstrap_values = []

                for class_id in CLASS_IDS:
                    point_ap = calculate_ap(
                        method_routes[method],
                        common_routes,
                        class_id,
                        iou,
                    )

                    bootstrap_ap = [
                        calculate_ap(
                            method_routes[method],
                            sample,
                            class_id,
                            iou,
                        )
                        for sample in bootstrap_samples
                    ]

                    ap_samples[
                        (method, class_id, iou)
                    ] = bootstrap_ap

                    summary_rows.append({
                        "weather": weather,
                        "method": method,
                        "class": CLASS_NAMES[class_id],
                        "class_id": class_id,
                        "iou": iou,
                        "routes": len(common_routes),
                        "ap": point_ap,
                        "ci95_low": percentile(
                            bootstrap_ap,
                            2.5,
                        ),
                        "ci95_high": percentile(
                            bootstrap_ap,
                            97.5,
                        ),
                        "iterations": args.iterations,
                        "seed": args.seed,
                    })

                    class_point_values.append(point_ap)
                    class_bootstrap_values.append(
                        np.asarray(
                            bootstrap_ap,
                            dtype=np.float64,
                        )
                    )

                point_map = float(np.nanmean(
                    class_point_values
                ))

                bootstrap_map = np.nanmean(
                    np.stack(
                        class_bootstrap_values,
                        axis=0,
                    ),
                    axis=0,
                )

                ap_samples[
                    (method, "map", iou)
                ] = bootstrap_map.tolist()

                summary_rows.append({
                    "weather": weather,
                    "method": method,
                    "class": "mAP",
                    "class_id": "all",
                    "iou": iou,
                    "routes": len(common_routes),
                    "ap": point_map,
                    "ci95_low": percentile(
                        bootstrap_map,
                        2.5,
                    ),
                    "ci95_high": percentile(
                        bootstrap_map,
                        97.5,
                    ),
                    "iterations": args.iterations,
                    "seed": args.seed,
                })

        # Paired bootstrap improvements relative to baseline.
        for method in available_methods:
            if method == "baseline":
                continue

            for iou in IOU_THRESHOLDS:
                for class_key, class_label in (
                    (0, "vehicle"),
                    (1, "pedestrian"),
                    (3, "bicycle"),
                    ("map", "mAP"),
                ):
                    baseline_values = np.asarray(
                        ap_samples[
                            ("baseline", class_key, iou)
                        ],
                        dtype=np.float64,
                    )

                    method_values = np.asarray(
                        ap_samples[
                            (method, class_key, iou)
                        ],
                        dtype=np.float64,
                    )

                    delta = (
                        method_values -
                        baseline_values
                    )

                    point_method = next(
                        row["ap"]
                        for row in summary_rows
                        if row["weather"] == weather
                        and row["method"] == method
                        and row["class"] == class_label
                        and float(row["iou"]) == float(iou)
                    )

                    point_baseline = next(
                        row["ap"]
                        for row in summary_rows
                        if row["weather"] == weather
                        and row["method"] == "baseline"
                        and row["class"] == class_label
                        and float(row["iou"]) == float(iou)
                    )

                    delta_rows.append({
                        "weather": weather,
                        "method": method,
                        "baseline": "baseline",
                        "class": class_label,
                        "iou": iou,
                        "routes": len(common_routes),
                        "ap_delta": (
                            float(point_method) -
                            float(point_baseline)
                        ),
                        "ci95_low": percentile(
                            delta,
                            2.5,
                        ),
                        "ci95_high": percentile(
                            delta,
                            97.5,
                        ),
                        "probability_improvement":
                            float(np.nanmean(delta > 0)),
                        "iterations": args.iterations,
                        "seed": args.seed,
                    })

    if not summary_rows:
        print("BOOTSTRAP=WAITING_FOR_INFERENCE")
        return

    summary_path = (
        output / "route_bootstrap_ap.tsv"
    )

    delta_path = (
        output / "route_bootstrap_delta.tsv"
    )

    manifest_path = (
        output / "route_bootstrap_manifest.tsv"
    )

    write_tsv(summary_path, summary_rows)
    write_tsv(delta_path, delta_rows)
    write_tsv(manifest_path, manifest_rows)

    print("AP_ROWS={}".format(len(summary_rows)))
    print("DELTA_ROWS={}".format(len(delta_rows)))
    print("MANIFEST_ROWS={}".format(
        len(manifest_rows)
    ))
    print("AP_OUTPUT={}".format(summary_path))
    print("DELTA_OUTPUT={}".format(delta_path))
    print("ROUTE_BOOTSTRAP_95CI=PASS")


if __name__ == "__main__":
    main()
