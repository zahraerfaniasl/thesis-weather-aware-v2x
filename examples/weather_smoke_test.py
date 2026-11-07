#!/usr/bin/env python3
"""Run the joint-weather package on a synthetic point cloud.

Needs only NumPy and works without V2Xverse, CARLA, or a GPU. It checks that
the response tables load and that a seeded run is repeatable. It does not
show that the weather model is realistic.

Run from anywhere:
    python examples/weather_smoke_test.py
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.weather_augmentation.joint_weather_cloud_stage9b import (  # noqa: E402
    ExperimentalJointWeather,
)

MANIFEST = os.path.join(
    ROOT, "src", "weather_augmentation", "tables", "manifest.json"
)
PMIN = 2.25e-05
BETA0 = 3.1830988618379064e-07
SEED = 2026
MAX_RANGE_M = 12.0  # The packaged tables stop at 13 m.


def synthetic_cloud(count=2000):
    """Return an Nx4 cloud with CARLA-like intensity, I = exp(-0.004 r)."""
    rng = np.random.RandomState(0)
    direction = rng.normal(size=(count, 3))
    direction /= np.linalg.norm(direction, axis=1, keepdims=True)
    distance = rng.uniform(1.0, MAX_RANGE_M, size=(count, 1))
    xyz = direction * distance
    return np.hstack([xyz, np.exp(-0.004 * distance)]).astype(np.float32)


def main():
    cloud = synthetic_cloud()
    for profile in ("RF2", "RF3"):
        model = ExperimentalJointWeather(MANIFEST, profile, PMIN, BETA0)
        first, info = model.augment(cloud, seed=SEED, enabled=True)
        second, _ = model.augment(cloud, seed=SEED, enabled=True)
        if not np.array_equal(first, second):
            raise SystemExit("Seeded output is not repeatable: " + profile)
        print(profile, "input", len(cloud), "output", len(first), info)
    print("PASS")


if __name__ == "__main__":
    main()
