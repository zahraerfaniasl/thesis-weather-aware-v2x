#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run the canonical granular Stage-9b closed-loop result audit."
        )
    )
    parser.add_argument(
        "--v2xverse-root",
        default=os.environ.get("V2XVERSE_ROOT"),
        help="V2Xverse repository root; defaults to V2XVERSE_ROOT.",
    )
    parser.add_argument(
        "--show-problems",
        type=int,
        default=20,
        help="Maximum number of problem records to display.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.v2xverse_root:
        print("ERROR: provide --v2xverse-root or set V2XVERSE_ROOT.")
        return 2

    repository_root = Path(__file__).resolve().parents[2]
    canonical_auditor = (
        repository_root
        / "scripts"
        / "closed_loop"
        / "audit_closed_loop_jobs.py"
    )

    if not canonical_auditor.is_file():
        print(
            "ERROR: canonical closed-loop auditor not found: {}".format(
                canonical_auditor
            )
        )
        return 2

    command = [
        sys.executable,
        str(canonical_auditor),
        "--v2xverse-root",
        str(Path(args.v2xverse_root).expanduser()),
        "--show-problems",
        str(max(args.show_problems, 0)),
    ]

    print("=== CLOSED-LOOP RESULT AUDIT ENTRYPOINT ===")
    print("canonical_auditor={}".format(canonical_auditor))
    print()

    completed = subprocess.run(command, check=False)

    print()
    print("delegated_exit_code={}".format(completed.returncode))

    if completed.returncode == 0:
        print("AUDIT_CLOSED_LOOP_RESULTS=PASS")
    else:
        print("AUDIT_CLOSED_LOOP_RESULTS=REVIEW")

    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
