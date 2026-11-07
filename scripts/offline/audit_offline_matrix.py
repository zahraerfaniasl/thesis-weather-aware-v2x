#!/usr/bin/env python3
import argparse
import csv
import os
import sys
from pathlib import Path

METHODS = (
    "baseline",
    "density",
    "density_doppler",
    "density_doppler_gate",
)

WEATHERS = ("OFF", "RF1", "RF2", "RF3")
EXPECTED = {(weather, method) for weather in WEATHERS for method in METHODS}

def parse_args():
    parser = argparse.ArgumentParser(
        description="Audit the 16-cell Stage-9b offline screening matrix."
    )
    parser.add_argument(
        "--output-root",
        default=os.environ.get("OFFLINE_OUTPUT_ROOT"),
        help="Matrix output directory containing offline_matrix_status.tsv.",
    )
    return parser.parse_args()

def resolve_record_path(value, output_root):
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = output_root / path
    return path.resolve()

def main():
    args = parse_args()

    if not args.output_root:
        print("ERROR: provide --output-root or set OFFLINE_OUTPUT_ROOT.")
        return 2

    output_root = Path(args.output_root).expanduser().resolve()
    status_file = output_root / "offline_matrix_status.tsv"

    if not status_file.is_file():
        print("ERROR: status file not found: {}".format(status_file))
        return 2

    with status_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"weather", "method", "rc", "model_dir", "log"}
        fields = set(reader.fieldnames or [])

        if not required.issubset(fields):
            print("ERROR: status file columns are incomplete.")
            print("columns={}".format(sorted(fields)))
            return 2

        rows = list(reader)

    seen = set()
    duplicates = []
    unexpected = []
    failed = []
    missing_logs = []
    empty_logs = []

    for row in rows:
        weather = row["weather"].strip()
        method = row["method"].strip()
        key = (weather, method)

        if key in seen:
            duplicates.append(key)
        seen.add(key)

        if key not in EXPECTED:
            unexpected.append(key)

        try:
            rc = int(row["rc"].strip())
        except ValueError:
            rc = -999

        if rc != 0:
            failed.append((weather, method, rc))

        log_path = resolve_record_path(row["log"], output_root)
        if not log_path.is_file():
            missing_logs.append((weather, method, log_path))
        elif log_path.stat().st_size == 0:
            empty_logs.append((weather, method, log_path))

    missing_cells = sorted(EXPECTED - seen)
    passed = len(EXPECTED) - len(failed) - len(missing_cells)

    print("=== OFFLINE MATRIX AUDIT ===")
    print("output_root={}".format(output_root))
    print("status_file={}".format(status_file))
    print("expected_cells={}".format(len(EXPECTED)))
    print("status_rows={}".format(len(rows)))
    print("unique_expected_cells={}".format(len(seen & EXPECTED)))
    print("passed_cells={}".format(passed))
    print("failed_cells={}".format(len(failed)))
    print("missing_cells={}".format(len(missing_cells)))
    print("duplicate_rows={}".format(len(duplicates)))
    print("unexpected_rows={}".format(len(unexpected)))
    print("missing_logs={}".format(len(missing_logs)))
    print("empty_logs={}".format(len(empty_logs)))

    for weather, method in missing_cells:
        print("MISSING weather={} method={}".format(weather, method))

    for weather, method, rc in failed:
        print("FAILED weather={} method={} rc={}".format(weather, method, rc))

    problems = (
        missing_cells
        or failed
        or duplicates
        or unexpected
        or missing_logs
        or empty_logs
        or len(rows) != len(EXPECTED)
    )

    print()
    if not problems:
        print("OFFLINE_MATRIX_AUDIT=PASS")
        return 0

    print("OFFLINE_MATRIX_AUDIT=INCOMPLETE")
    return 1

if __name__ == "__main__":
    sys.exit(main())
