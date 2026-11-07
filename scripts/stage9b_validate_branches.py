#!/usr/bin/env python
import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime

import yaml

ROOT = Path(os.environ["V2XVERSE_ROOT"])
PIPE = ROOT / "results/stage9b_pipeline"
BRANCH = PIPE / "branch_run"
ENTRY = ROOT / "opencood/tools/inference_stage9b_validation.py"
EVALUATOR = ROOT / "opencood/utils/eval_utils_stage9b_validation.py"
INDEX = ROOT / "results/stage9b7_index/val/dataset_index.txt"
METHODS = ("baseline", "density", "density_doppler", "density_doppler_gate")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n"
    )
    temporary.replace(path)


def stopped(unit):
    state = subprocess.check_output(
        ["systemctl", "--user", "show", unit,
         "--property=ActiveState", "--value"],
        universal_newlines=True,
    ).strip()
    require(state in ("inactive", "failed"),
            "{} is {}".format(unit, state))


def validate_outputs(view, expected_routes, expected_samples):
    text = (view / "inference.log").read_text(errors="replace")
    counts = {}
    for line in text.splitlines():
        for key in (
            "VALIDATION_DATASET_SAMPLES",
            "VALIDATION_BATCHES_SEEN",
            "VALIDATION_USABLE_BATCHES",
            "VALIDATION_NONE_BATCHES",
        ):
            if line.startswith(key + "="):
                counts[key] = int(line.split("=", 1)[1])

    for key in (
        "VALIDATION_DATASET_SAMPLES",
        "VALIDATION_BATCHES_SEEN",
        "VALIDATION_USABLE_BATCHES",
    ):
        require(counts.get(key) == expected_samples,
                "{} mismatch: {}".format(key, counts))
    require(counts.get("VALIDATION_NONE_BATCHES") == 0,
            "Skipped/None samples require review")

    payload = json.loads(
        (view / "route_detection_stats.json").read_text()
    )
    routes = payload.get("routes", {})
    require(set(routes) == expected_routes,
            "Recorded routes differ from validation index")
    require(payload.get("class_ids") == [0, 1, 3],
            "Unexpected class IDs")

    with (view / "gate_telemetry.tsv").open(newline="") as stream:
        telemetry = list(csv.DictReader(stream, delimiter="\t"))
    require(len(telemetry) == expected_samples,
            "Telemetry row count differs from sample count")

    files = list(view.glob("eval_*.yaml"))
    require(len(files) == 1, "Expected exactly one evaluation YAML")
    metrics = yaml.safe_load(files[0].read_text())
    aggregate = {}

    for class_id in (0, 1, 3):
        class_result = metrics[class_id]
        class_counts = {}
        for threshold, ap_key in (
            ("0.3", "ap30"), ("0.5", "ap50"), ("0.7", "ap70")
        ):
            gt = predictions = true_pos = false_pos = 0
            for route in routes.values():
                item = route[str(class_id)][threshold]
                tp, fp, scores = item["tp"], item["fp"], item["score"]
                require(len(tp) == len(fp) == len(scores),
                        "TP/FP/score lengths differ")
                require(all(a in (0, 1) and b in (0, 1) and a+b == 1
                            for a, b in zip(tp, fp)),
                        "Invalid TP/FP flags")
                require(all(math.isfinite(float(s)) for s in scores),
                        "Nonfinite detection score")
                n = item["gt"]
                require(isinstance(n, int) and n >= 0,
                        "Invalid GT count")
                require(sum(tp) <= n, "TP exceeds GT within route")
                gt += n
                predictions += len(scores)
                true_pos += sum(tp)
                false_pos += sum(fp)

            ap = class_result[ap_key]
            if gt == 0:
                require(ap is None, "AP must be null when GT is zero")
            else:
                require(
                    isinstance(ap, (int, float))
                    and math.isfinite(ap) and 0 <= ap <= 1,
                    "Invalid AP for class with GT"
                )
            class_counts[threshold] = {
                "gt": gt, "predictions": predictions,
                "tp": true_pos, "fp": false_pos, "ap": ap,
            }

        require(len({v["gt"] for v in class_counts.values()}) == 1,
                "GT count differs across IoU thresholds")
        require(len({v["predictions"] for v in class_counts.values()}) == 1,
                "Prediction count differs across IoU thresholds")
        require(class_result["gt_count"] == class_counts["0.5"]["gt"],
                "Metric GT count differs from route statistics")
        require(class_result["prediction_count"] ==
                class_counts["0.5"]["predictions"],
                "Metric prediction count differs from route statistics")
        aggregate[str(class_id)] = class_counts

    return {
        "status": "STRUCTURAL_CHECKS_PASS",
        "sample_counts": counts,
        "route_count": len(routes),
        "classes": aggregate,
        "scientific_review_required": True,
        "occluded_actor_metrics_verified": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("check", "run"))
    args = parser.parse_args()
    os.chdir(str(ROOT))

    for path in (ENTRY, EVALUATOR):
        require(path.is_file(), "Missing file: " + str(path))
        compile(path.read_text(), str(path), "exec")

    expected_routes = set()
    expected_samples = 0
    for line in INDEX.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split()
        require(len(parts) == 3, "Malformed index entry")
        route, frames, egos = parts
        require("_town04_" in route, "Non-Town04 validation entry")
        require(route not in expected_routes, "Duplicate route entry")
        require(int(egos) == 1,
                "Runner currently expects one ego per route")
        require(int(frames) > 0, "Nonpositive frame count")
        expected_routes.add(route)
        expected_samples += int(frames)

    require(expected_routes, "Empty validation index")
    print("VALIDATION_ROUTES={}".format(len(expected_routes)), flush=True)
    print("EXPECTED_SAMPLES={}".format(expected_samples), flush=True)

    ready = {}
    for method in METHODS:
        done = BRANCH / method / "complete.json"
        if not done.is_file():
            print("MODEL_PENDING=" + method, flush=True)
            continue
        info = json.loads(done.read_text())
        model = Path(info["model_dir"]).resolve()
        weights = model / "net_epoch1.pth"
        config = model / "config.yaml"
        require(config.is_file() and weights.is_file(),
                "Completed model files missing: " + method)
        require(sha(weights) == info["checkpoint_sha256"],
                "Checkpoint hash mismatch: " + method)
        ready[method] = (info, weights, config)
        print("MODEL_READY=" + method, flush=True)

    if args.mode == "check":
        print("VALIDATION_RUNNER_CHECK=PASS")
        print("MODELS_READY={}/4".format(len(ready)))
        print("GPU_EVALUATION_STARTED=NO")
        return

    require(len(ready) == 4, "All four completed branches are required")
    protocol = json.loads((BRANCH / "protocol.json").read_text())
    for method, (info, _, _) in ready.items():
        require(info["shared_sha256"] == protocol["checkpoint_sha256"],
                "Shared initialization mismatch: " + method)

    with (PIPE / "full_validation.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for unit in (
            "stage9b-branches.service",
            "stage9b-shared-baseline.service",
            "stage9b-after-shared.service",
        ):
            stopped(unit)

        processes = subprocess.run(
            ["pgrep", "-af",
             "[o]pencood/tools/train[^ ]*\\.py|"
             "[o]pencood/tools/inference[^ ]*\\.py|"
             "[l]eaderboard_evaluator_parameter.py|[C]arlaUE4"],
            stdout=subprocess.PIPE, universal_newlines=True,
        )
        require(processes.returncode == 1,
                "GPU process check blocked:\n" + processes.stdout)

        session = PIPE / "validation_views" / (
            "suite_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        session.mkdir(parents=True, exist_ok=False)
        inputs = {str(p): sha(p) for p in (ENTRY, EVALUATOR, INDEX)}
        save(session / "inputs.json", {
            "hashes": inputs, "methods": list(METHODS),
            "expected_samples": expected_samples,
            "checkpoint_policy": "branch net_epoch1.pth",
            "scope": "Town04 standard validation only",
        })
        print("SESSION=" + str(session), flush=True)

        environment = os.environ.copy()
        environment.update({
            "PYTHONPATH": str(ROOT), "PYTHONUNBUFFERED": "1",
            "CUDA_VISIBLE_DEVICES": "0", "MPLBACKEND": "Agg",
            "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2",
            "PYTHONHASHSEED": "2026",
        })

        for method in METHODS:
            require(all(sha(Path(p)) == h for p, h in inputs.items()),
                    "Validation inputs changed during suite")
            info, weights, config = ready[method]
            view = session / method
            view.mkdir()
            for src in (weights, config):
                shutil.copy2(str(src), str(view / src.name))
            require(sha(view / weights.name) == info["checkpoint_sha256"],
                    "Copied checkpoint hash mismatch")
            save(view / "provenance.json", {
                "method": method, "branch_completion": info,
                "copied_config_sha256": sha(view / "config.yaml"),
            })

            print("START={} VIEW={}".format(method, view), flush=True)
            with (view / "inference.log").open("w") as stream:
                result = subprocess.run(
                    [sys.executable, str(ENTRY),
                     "--model_dir", str(view),
                     "--fusion_method", "intermediate",
                     "--max_samples", "0",
                     "--save_vis_interval", "1000000",
                     "--note", "_" + method],
                    cwd=str(ROOT), env=environment,
                    stdout=stream, stderr=subprocess.STDOUT,
                )
            require(result.returncode == 0,
                    "Inference failed; inspect " + str(view / "inference.log"))
            require(all(sha(Path(p)) == h for p, h in inputs.items()),
                    "Validation inputs changed during inference")
            report = validate_outputs(
                view, expected_routes, expected_samples
            )
            save(view / "validated_output.json", report)
            print("STRUCTURAL_CHECKS_PASS=" + method, flush=True)

        save(session / "suite_complete.json", {
            "status": "FOUR_VALIDATION_RUNS_STRUCTURALLY_CHECKED",
            "methods": list(METHODS),
            "scientific_review_required": True,
        })
        print("VALIDATION_SUITE=COMPLETED_REVIEW_REQUIRED", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("VALIDATION_RUNNER=FAIL: " + str(error),
              file=sys.stderr, flush=True)
        raise SystemExit(1)
