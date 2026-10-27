"""Experimental rain-fog point-cloud augmentation.

NOT sensor-calibrated and NOT a reproduction of full Hahner outputs.
Output intensity convention: selected power * selected range**2.
No output clipping, range noise, or intensity quantization.
Requires sensor-local XYZ in metres and input intensity in [0, 1].
Not connected to the online agent or dataset by this module.
"""
from pathlib import Path
import hashlib
import json
import numpy as np

from .joint_weather_return_core_stage9b import (
    candidate_powers, select_strongest,
)
from .joint_weather_rain_sampler_stage9b import (
    sample_strongest_rain,
)


class ExperimentalJointWeather:
    def __init__(self, manifest_path, profile, pmin, beta0):
        self.pmin = float(pmin)
        self.beta0 = float(beta0)
        if not np.isfinite(self.pmin) or self.pmin < 0:
            raise ValueError("Invalid explicit detection threshold")
        if not np.isfinite(self.beta0) or self.beta0 <= 0:
            raise ValueError("Invalid explicit beta0")

        manifest_file = Path(manifest_path).expanduser().resolve()
        manifest = json.loads(
            manifest_file.read_text(encoding="utf-8")
        )
        matches = [
            item for item in manifest["profiles"]
            if item["profile"] == profile
        ]
        if len(matches) != 1:
            raise ValueError("Profile must identify exactly one table")

        self.profile = dict(matches[0])
        path = Path(self.profile["table"]).expanduser()
        if not path.is_absolute():
            path = manifest_file.parent / path
        path = path.resolve()
        if hashlib.sha256(path.read_bytes()).hexdigest() != self.profile["sha256"]:
            raise ValueError("Table hash mismatch")

        with np.load(str(path), allow_pickle=False) as data:
            self.grid = data["target_range_m"].copy()
            self.peak = data["fog_peak_range_m"].copy()
            self.integral = data["normalized_fog_integral"].copy()
            for key, field in (
                ("alpha_total", "alpha_total_per_m"),
                ("alpha_rain", "alpha_rain_per_m"),
                ("alpha_fog", "alpha_fog_per_m"),
                ("beta_fog", "beta_fog"),
            ):
                if not np.isclose(
                    float(data[key]), float(self.profile[field]),
                    rtol=1e-12, atol=1e-15,
                ):
                    raise ValueError("Table metadata mismatch: " + key)

        arrays = (self.grid, self.peak, self.integral)
        if self.grid.ndim != 1 or len(self.grid) < 2:
            raise ValueError("Invalid table grid")
        if any(a.shape != self.grid.shape for a in arrays):
            raise ValueError("Table shape mismatch")
        if any(not np.isfinite(a).all() or np.any(a < 0) for a in arrays):
            raise ValueError("Invalid table values")
        if not np.all(np.diff(self.grid) > 0):
            raise ValueError("Table grid must increase")
        if self.profile.get("distance_convention") != "unshifted_grid_peak":
            raise ValueError("Unsupported distance convention")
        if not np.isclose(
            self.grid[-1], self.profile["target_range_max_m"]
        ):
            raise ValueError("Table range mismatch")
        if not np.isclose(
            self.profile["alpha_total_per_m"],
            self.profile["alpha_rain_per_m"]
            + self.profile["alpha_fog_per_m"],
        ):
            raise ValueError("Extinction coefficients do not add up")

    def augment(self, point_cloud, seed, enabled=True):
        pc = np.asarray(point_cloud)
        if pc.ndim != 2 or pc.shape[1] != 4:
            raise ValueError("Expected floating-point Nx4 sensor-local cloud")
        if not np.issubdtype(pc.dtype, np.floating):
            raise ValueError("Expected floating-point cloud")

        # Explicit bypass: exact values and dtype, no random draws.
        if not enabled:
            return pc.copy(), {
                "enabled": False,
                "input_points": len(pc),
                "output_points": len(pc),
            }

        if not np.isfinite(pc).all():
            raise ValueError("Nonfinite input; no silent filtering")
        if np.any((pc[:, 3] < 0) | (pc[:, 3] > 1)):
            raise ValueError("Intensity outside [0, 1]; no auto-rescaling")
        if not isinstance(seed, (int, np.integer)) or isinstance(seed, bool):
            raise ValueError("Seed must be an integer")
        if not 0 <= int(seed) <= 4294967295:
            raise ValueError("Seed outside RandomState range")

        xyz = pc[:, :3].astype(np.float64)
        ranges = np.linalg.norm(xyz, axis=1)
        if np.any(ranges <= 0):
            raise ValueError("Zero-range points need an explicit handling policy")
        if np.any(ranges < self.grid[0]) or np.any(ranges > self.grid[-1]):
            raise ValueError("Target outside fog table range; no clipping")

        # Nearest table node; ties choose the lower node.
        hi = np.searchsorted(self.grid, ranges, side="left")
        hi = np.minimum(hi, len(self.grid) - 1)
        lo = np.maximum(hi - 1, 0)
        choose_hi = (
            np.abs(self.grid[hi] - ranges)
            < np.abs(ranges - self.grid[lo])
        )
        index = np.where(choose_hi, hi, lo)

        rng = np.random.RandomState(int(seed))
        rain = sample_strongest_rain(
            ranges,
            self.profile["rain_rate_mm_h"],
            self.profile["alpha_total_per_m"],
            rng,
        )
        powers = candidate_powers(
            ranges,
            pc[:, 3].astype(np.float64),
            self.profile["alpha_total_per_m"],
            self.integral[index],
            self.profile["beta_fog"],
            self.beta0,
            rain["power"],
        )
        candidate_ranges = np.column_stack((
            ranges, rain["range_m"], self.peak[index],
        ))
        selected = select_strongest(
            candidate_ranges, powers, self.pmin
        )
        valid = selected["valid"]
        indices = np.flatnonzero(valid)
        selected_ranges = selected["range_m"][valid]
        intensity = selected["power"][valid] * selected_ranges**2

        if not np.isfinite(intensity).all():
            raise ValueError("Nonfinite output intensity")
        if np.any((intensity < 0) | (intensity > 1)):
            raise ValueError(
                "Output outside intensity contract; no hidden clipping"
            )

        out = np.empty((len(indices), 4), dtype=pc.dtype)
        out[:, :3] = xyz[valid] * (
            selected_ranges / ranges[valid]
        )[:, None]
        out[:, 3] = intensity
        if not np.isfinite(out).all():
            raise ValueError("Nonfinite output after dtype conversion")

        labels = selected["labels"]
        info = {
            "enabled": True,
            "profile": self.profile["profile"],
            "seed": int(seed),
            "input_points": len(pc),
            "output_points": len(out),
            "lost": int(np.count_nonzero(labels == 0)),
            "rain": int(np.count_nonzero(labels == 1)),
            "hard": int(np.count_nonzero(labels == 2)),
            "fog": int(np.count_nonzero(labels == 3)),
            "sampled_rain_drops": int(rain["sampled_count"].sum()),
            "max_table_distance_error_m": (
                float(np.max(np.abs(self.grid[index] - ranges)))
                if len(ranges) else 0.0
            ),
            "output_intensity_convention": "selected_power_times_selected_range_squared",
            "range_noise_enabled": False,
            "sensor_calibrated": False,
        }
        return out, info
