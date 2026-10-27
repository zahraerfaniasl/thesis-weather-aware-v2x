"""Opt-in dataset bridge for experimental joint rain-fog weather."""
import hashlib
import json
import numpy as np


def validate_joint_weather(params, legacy_agent_rain=None):
    cfg = params.get("stage9b_joint_weather", {})
    if not isinstance(cfg, dict):
        raise ValueError("stage9b_joint_weather must be a mapping")
    enabled = cfg.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("Weather enabled must be a YAML boolean")
    if not enabled:
        return None

    if params.get("adverse_weather", {}).get("enabled", False):
        raise ValueError("New weather and legacy dataset weather both enabled")
    if legacy_agent_rain is not None and legacy_agent_rain is not False:
        raise ValueError("Explicitly disable legacy_rsu_rain in agent config")

    required = ("manifest_path", "profile", "pmin", "beta0",
                "base_seed", "seed_policy")
    for key in required:
        if key not in cfg:
            raise ValueError("Missing joint-weather setting: " + key)

    if cfg["seed_policy"] != "content_role_v1":
        raise ValueError("Unsupported weather seed policy")
    if cfg["profile"] not in ("RF1", "RF2", "RF3"):
        raise ValueError("Unsupported weather profile")
    if type(cfg["base_seed"]) is not int:
        raise ValueError("base_seed must be an integer")
    if not 0 <= cfg["base_seed"] <= 4294967295:
        raise ValueError("base_seed outside uint32 range")

    for key in ("pmin", "beta0"):
        value = float(cfg[key])
        if not np.isfinite(value) or value < 0:
            raise ValueError("Invalid " + key)
    if float(cfg["beta0"]) == 0:
        raise ValueError("beta0 must be positive")
    return dict(cfg)


def content_seed(pc, role, base_seed):
    if role not in ("ego", "other_ego", "rsu"):
        raise ValueError("Unknown sensor role")
    # Explicit canonical representation, independent of native endianness.
    array = np.asarray(pc)
    if array.ndim != 2 or array.shape[1] != 4:
        raise ValueError("Expected Nx4 cloud")
    canonical = np.ascontiguousarray(array, dtype="<f4")
    header = json.dumps(
        ["content_role_v1", int(base_seed), role, list(canonical.shape)],
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(header + canonical.tobytes()).digest()
    return int.from_bytes(digest[:4], byteorder="little")


def apply_joint_weather(owner, lidar, role):
    cfg = validate_joint_weather(owner.params)
    if cfg is None:
        return lidar, None

    signature = json.dumps(cfg, sort_keys=True)
    cached = getattr(owner, "_stage9b_joint_weather_cache", None)

    if cached is None:
        from .joint_weather_cloud_stage9b import (
            ExperimentalJointWeather,
        )
        model = ExperimentalJointWeather(
            cfg["manifest_path"], cfg["profile"],
            pmin=cfg["pmin"], beta0=cfg["beta0"],
        )
        cached = (signature, model)
        owner._stage9b_joint_weather_cache = cached
    elif cached[0] != signature:
        raise RuntimeError("Weather configuration changed after initialization")

    seed = content_seed(lidar, role, cfg["base_seed"])
    output, info = cached[1].augment(lidar, seed=seed, enabled=True)
    info = dict(info)
    info["sensor_role"] = role
    info["seed_policy"] = cfg["seed_policy"]

    count = getattr(owner, "_stage9b_joint_weather_trace_count", 0)
    if count < 3:
        print("JOINT_WEATHER_TRACE=" + json.dumps(info, sort_keys=True))
        owner._stage9b_joint_weather_trace_count = count + 1

    return output, info
