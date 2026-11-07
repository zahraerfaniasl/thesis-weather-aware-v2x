#!/usr/bin/env python
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import yaml

ROOT = Path(os.environ["V2XVERSE_ROOT"])
PIPE = ROOT / "results/stage9b_pipeline"
TEMPLATES = PIPE / "branch_templates"
RUN = PIPE / "branch_run"
TRAINER = ROOT / "opencood/tools/train_stage9b_branch.py"
PYTHON = os.environ.get("PYTHON", "python")

METHODS = (
    "baseline", "density",
    "density_doppler", "density_doppler_gate",
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_text(path, text):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def save_json(path, value):
    atomic_text(path, json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--checkpoint")
    args = parser.parse_args()

    os.chdir(str(ROOT))

    configs = {}
    for method in METHODS:
        path = TEMPLATES / (method + ".yaml")
        with path.open() as stream:
            config = yaml.safe_load(stream)

        train = config["train_params"]
        assert train["epoches"] == 1, method
        assert train["batch_size"] == 1, method
        assert train.get("max_train_batches") is None, method
        assert train.get("max_val_batches") is None, method
        assert train.get("run_test_after_training") is False, method
        assert config["optimizer"]["lr"] == 0.0002, method
        assert config["validation_towns"] == [4], method
        configs[method] = config
        print("TEMPLATE_OK=" + method, flush=True)

    compile(TRAINER.read_text(), str(TRAINER), "exec")

    if args.mode == "check":
        print("BRANCH_RUNNER_CHECK=PASS")
        print("CHECKPOINT_COMPATIBILITY=NOT_TESTED_YET")
        print("NEW_TRAINING_STARTED=NO")
        return

    if not args.checkpoint:
        raise RuntimeError("run requires --checkpoint PATH")

    checkpoint = Path(args.checkpoint).expanduser().resolve()
    if not checkpoint.is_file():
        raise RuntimeError("Checkpoint missing: " + str(checkpoint))

    finalized = PIPE / "markers/31_dataset_finalized"
    if not finalized.is_file():
        raise RuntimeError("Dataset finalization marker missing")

    RUN.mkdir(parents=True, exist_ok=True)

    with (RUN / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

        active = subprocess.run(
            ["pgrep", "-af",
             "opencood/tools/train.py|"
             "opencood/tools/train_stage9b_branch.py|"
             "leaderboard_evaluator_parameter.py|CarlaUE4"],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        if active.returncode == 0:
            raise RuntimeError("Other GPU workload active:\n" + active.stdout)
        if active.returncode != 1:
            raise RuntimeError("Process check failed")

        service = subprocess.check_output(
            ["systemctl", "--user", "show",
             "stage9b-shared-baseline.service",
             "--property=ActiveState", "--value"],
            universal_newlines=True,
        ).strip()
        if service not in ("inactive", "failed"):
            raise RuntimeError("Shared Baseline service is not stopped")

        # Bind this run to immutable code, configs and dataset indexes.
        inputs = [
            TRAINER,
            ROOT / "opencood/models/center_point_codriving.py",
        ]
        inputs += [TEMPLATES / (m + ".yaml") for m in METHODS]
        inputs += [
            ROOT / "results/stage9b7_index" / split / "dataset_index.txt"
            for split in ("train", "val", "test")
        ]

        protocol = {
            "checkpoint_sha256": digest(checkpoint),
            "input_hashes": {str(p): digest(p) for p in inputs},
            "methods": list(METHODS),
            "epochs_per_branch": 1,
            "seed": 2026,
        }
        protocol_file = RUN / "protocol.json"

        if protocol_file.exists():
            if json.loads(protocol_file.read_text()) != protocol:
                raise RuntimeError(
                    "Run inputs changed. Do not mix results from different runs."
                )
        else:
            save_json(protocol_file, protocol)

        frozen = RUN / "shared_initialization.pth"
        if not frozen.exists():
            temporary = RUN / "shared_initialization.pth.tmp"
            shutil.copy2(str(checkpoint), str(temporary))
            if digest(temporary) != protocol["checkpoint_sha256"]:
                raise RuntimeError("Checkpoint changed during copy")
            temporary.replace(frozen)

        if digest(frozen) != protocol["checkpoint_sha256"]:
            raise RuntimeError("Frozen checkpoint hash mismatch")

        environment = os.environ.copy()
        environment.update({
            "PYTHONPATH": str(ROOT),
            "PYTHONUNBUFFERED": "1",
            "PYTHONHASHSEED": "2026",
            "CUDA_VISIBLE_DEVICES": "0",
            "OMP_NUM_THREADS": "2",
            "MKL_NUM_THREADS": "2",
            "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:128",
        })

        model_dirs = {}

        for method in METHODS:
            work = RUN / method
            work.mkdir(exist_ok=True)
            done = work / "complete.json"

            if done.exists():
                info = json.loads(done.read_text())
                model_dir = Path(info["model_dir"])
                weights = model_dir / "net_epoch1.pth"
                if not weights.is_file():
                    raise RuntimeError("Completed checkpoint missing: " + method)
                if digest(weights) != info["checkpoint_sha256"]:
                    raise RuntimeError("Completed checkpoint changed: " + method)
                model_dirs[method] = model_dir
                print("SKIP_COMPLETED=" + method, flush=True)
                continue

            config = configs[method]
            record = work / "model_dir.txt"
            config["stage9b_init_checkpoint"] = str(frozen)
            config["stage9b_model_dir_record"] = str(record)
            config["stage9b_seed"] = 2026

            config_path = work / "config.yaml"
            with config_path.open("w") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)

            # Never accept a directory record left by a failed attempt.
            if record.exists():
                record.unlink()

            log = work / "training.log"
            print("START={} LOG={}".format(method, log), flush=True)

            with log.open("a") as stream:
                stream.write("\n===== NEW BRANCH ATTEMPT =====\n")
                stream.flush()
                result = subprocess.run(
                    [PYTHON, str(TRAINER),
                     "--hypes_yaml", str(config_path),
                     "--fusion_method", "intermediate"],
                    cwd=str(ROOT), env=environment,
                    stdout=stream, stderr=subprocess.STDOUT,
                )

            if result.returncode != 0 or not record.is_file():
                raise RuntimeError("Training failed: {} LOG={}".format(method, log))

            model_dir = Path(record.read_text().strip())
            weights = model_dir / "net_epoch1.pth"
            if not weights.is_file() or weights.stat().st_size == 0:
                raise RuntimeError("Final checkpoint missing: " + method)

            save_json(done, {
                "method": method,
                "model_dir": str(model_dir),
                "checkpoint_sha256": digest(weights),
                "shared_sha256": protocol["checkpoint_sha256"],
            })
            model_dirs[method] = model_dir
            print("PASS=" + method, flush=True)

        lines = ["# Four branches completed; one shared initialization"]
        for method in METHODS:
            lines.append(
                "export STAGE9B_{}_MODEL_DIR={}".format(
                    method.upper(), shlex.quote(str(model_dirs[method]))
                )
            )

        env_file = PIPE / "model_dirs.env"
        if env_file.exists():
            backup = PIPE / ("model_dirs.env.backup_" + digest(env_file)[:12])
            if not backup.exists():
                shutil.copy2(str(env_file), str(backup))

        atomic_text(env_file, "\n".join(lines) + "\n")
        print("MODEL_ENV=" + str(env_file))
        print("FOUR_BRANCH_TRAINING=PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("BRANCH_RUNNER=FAIL: " + str(error), file=sys.stderr)
        raise SystemExit(1)
