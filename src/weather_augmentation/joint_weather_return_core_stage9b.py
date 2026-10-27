"""Experimental joint-weather candidate comparison.

Not a complete point-cloud augmentor or a calibrated sensor model.
Candidate order: hard target, strongest sampled rain drop, fog peak.
Powers are relative comparison scores, not measured watts.

No intensity quantization, saturation, range noise, or rain sampling
is performed here. Original LISA/Hahner final-output parity is NOT
claimed.
"""
import numpy as np


def _vector(value, name):
    value = np.asarray(value, dtype=np.float64)
    if value.ndim != 1 or not np.isfinite(value).all():
        raise ValueError(name + " must be a finite 1-D array")
    return value


def _scalar(value, name, positive=False):
    value = float(value)
    if not np.isfinite(value):
        raise ValueError(name + " must be finite")
    if value < 0 or (positive and value == 0):
        raise ValueError(name + " has an invalid sign")
    return value


def candidate_powers(
        target_range_m,
        input_intensity,
        alpha_total,
        normalized_fog_integral,
        beta_fog,
        beta0,
        rain_power):
    """Build [N, 3] comparison scores.

    rain_power must already include attenuation under alpha_total.
    Do not attenuate it a second time here.

    Fog comparison uses the unrounded, unsaturated Hahner-style
    response divided by ORIGINAL target_range_m**2.
    """
    r = _vector(target_range_m, "target_range_m")
    intensity = _vector(input_intensity, "input_intensity")
    integral = _vector(normalized_fog_integral, "fog_integral")
    rain = _vector(rain_power, "rain_power")

    if any(v.shape != r.shape for v in (intensity, integral, rain)):
        raise ValueError("Candidate arrays must have identical shapes")
    if np.any(r <= 0):
        raise ValueError("Target ranges must be strictly positive")
    if np.any((intensity < 0) | (intensity > 1)):
        raise ValueError("Expected intensity in [0, 1]; no auto-rescaling")
    if np.any(integral < 0) or np.any(rain < 0):
        raise ValueError("Negative candidate response")

    alpha = _scalar(alpha_total, "alpha_total")
    beta = _scalar(beta_fog, "beta_fog")
    beta0 = _scalar(beta0, "beta0", positive=True)

    hard = intensity * np.exp(-2.0 * alpha * r) / np.square(r)
    fog = intensity * integral * beta / beta0
    powers = np.column_stack((hard, rain, fog))

    if not np.isfinite(powers).all():
        raise ValueError("Nonfinite candidate powers")
    return powers


def select_strongest(candidate_ranges_m, powers, pmin):
    """Select one return per input point.

    Labels:
        0 = below threshold / no positive response
        1 = rain
        2 = hard target
        3 = fog

    pmin must be chosen explicitly; this module supplies no sensor
    calibration. Ties prefer hard, then rain, then fog.
    """
    ranges = np.asarray(candidate_ranges_m, dtype=np.float64)
    powers = np.asarray(powers, dtype=np.float64)
    threshold = _scalar(pmin, "pmin")

    if powers.ndim != 2 or powers.shape[1] != 3:
        raise ValueError("powers must have shape [N, 3]")
    if ranges.shape != powers.shape:
        raise ValueError("ranges and powers must have identical shapes")
    if not np.isfinite(ranges).all() or not np.isfinite(powers).all():
        raise ValueError("Nonfinite candidate input")
    if np.any(ranges < 0) or np.any(powers < 0):
        raise ValueError("Negative range or power")
    if np.any((powers > 0) & (ranges <= 0)):
        raise ValueError("Positive-power candidate needs positive range")

    winner = np.argmax(powers, axis=1)
    rows = np.arange(len(winner))
    selected_power = powers[rows, winner]
    selected_range = ranges[rows, winner]

    valid = (selected_power > 0) & (selected_power >= threshold)
    labels = np.array([2, 1, 3], dtype=np.uint8)[winner]
    labels = np.where(valid, labels, 0).astype(np.uint8)

    return {
        "labels": labels,
        "valid": valid,
        "range_m": np.where(valid, selected_range, 0.0),
        "power": np.where(valid, selected_power, 0.0),
    }
