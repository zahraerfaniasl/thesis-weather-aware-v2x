"""Experimental rain candidates for the stage9b joint-weather model.

Sampling follows the supplied LISA strongest-return implementation.
alpha_total is provided by the caller: attenuation is applied once.
No hard-target noise, fog response, or final intensity conversion here.
Uses a caller-owned NumPy RandomState; no global RNG mutation.
"""
import numpy as np


def sample_strongest_rain(
        target_range_m, rain_rate_mm_h, alpha_total, rng,
        rmin=1.5, bdiv=3e-3, dst=0.05, refractive_index=1.328,
        max_particles_per_ray=100000):
    r = np.asarray(target_range_m, dtype=np.float64)
    if r.ndim != 1 or not np.isfinite(r).all() or np.any(r <= 0):
        raise ValueError("Ranges must be finite, positive and 1-D")
    if not isinstance(rng, np.random.RandomState):
        raise TypeError("Pass an independent np.random.RandomState")

    rate = float(rain_rate_mm_h)
    alpha = float(alpha_total)
    parameters = np.asarray(
        [rate, alpha, rmin, bdiv, dst, refractive_index],
        dtype=np.float64,
    )
    if not np.isfinite(parameters).all():
        raise ValueError("Nonfinite parameter")
    if rate < 0 or alpha < 0 or rmin < 0 or dst <= 0:
        raise ValueError("Invalid rain/attenuation/range/diameter parameter")
    if not 0 < bdiv < np.pi / 2 or refractive_index <= 0:
        raise ValueError("Invalid divergence or refractive index")
    if int(max_particles_per_ray) != max_particles_per_ray:
        raise ValueError("Particle limit must be an integer")
    if max_particles_per_ray <= 0:
        raise ValueError("Particle limit must be positive")

    power = np.zeros(len(r), dtype=np.float64)
    distance = np.zeros(len(r), dtype=np.float64)
    diameter = np.zeros(len(r), dtype=np.float64)
    counts = np.zeros(len(r), dtype=np.int64)

    if rate == 0:
        return {
            "power": power, "range_m": distance,
            "diameter_mm": diameter, "sampled_count": counts,
        }

    slope = 4.1 * rate**(-0.21)
    density = 8000.0 * np.exp(-slope * dst) / slope
    fresnel = abs((refractive_index - 1) / (refractive_index + 1))**2

    def beam_diameter_mm(range_m):
        return 1e3 * np.tan(bdiv) * range_m

    for i, original_range in enumerate(r):
        if original_range > rmin:
            volume = (
                np.pi / 3 * original_range
                * (1e-3 * beam_diameter_mm(original_range) / 2)**2
            )
            expected = density * volume
            if not np.isfinite(expected) or expected > max_particles_per_ray:
                raise ValueError("Particle budget exceeded; no silent clipping")
            count = int(
                np.floor(expected)
                + (rng.rand() < expected - int(expected))
            )
        else:
            count = 0

        droplet_ranges = original_range * rng.rand(count)**(1.0 / 3.0)
        droplet_ranges = droplet_ranges[droplet_ranges > rmin]
        count = len(droplet_ranges)
        counts[i] = count
        if count == 0:
            continue

        diameters = -np.log(1 - rng.rand(count)) / slope + dst
        coverage = np.minimum(
            (diameters / beam_diameter_mm(droplet_ranges))**2, 1.0
        )
        candidates = (
            fresnel * np.exp(-2 * alpha * droplet_ranges)
            * coverage / droplet_ranges**2
        )
        if not np.isfinite(candidates).all():
            raise ValueError("Nonfinite droplet power")

        winner = int(np.argmax(candidates))
        if candidates[winner] > 0:
            power[i] = candidates[winner]
            distance[i] = droplet_ranges[winner]
            diameter[i] = diameters[winner]

    return {
        "power": power, "range_m": distance,
        "diameter_mm": diameter, "sampled_count": counts,
    }
