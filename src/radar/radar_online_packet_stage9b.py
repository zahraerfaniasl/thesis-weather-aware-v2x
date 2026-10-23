"""Online packet adapter using the existing offline-equivalent encoder."""
import numpy as np
from opencood.data_utils.radar.radar_runtime_stage9b import (
    encode_runtime_radar_to_ego,
)

def encode_online_rsu_packet(packet, ego_pose):
    """Return [4,192,576]; channels and geometry match the offline encoder.

    This preserves the upstream yaw-only transformation.
    Age is the sensor packet age, not a communication-latency model.
    """
    empty = np.zeros((4, 192, 576), dtype=np.float32)
    if packet is None:
        return empty
    if not isinstance(packet, dict):
        raise TypeError("Online RSU packet must be a dict")

    if not bool(packet.get("radar_packet_available", False)):
        return empty
    if bool(packet.get("radar_is_stale", False)):
        return empty

    age = packet.get("radar_age_frames")
    if age is None:
        raise ValueError("Available Radar packet has no radar_age_frames")
    age = float(age)
    if not np.isfinite(age):
        raise ValueError("Non-finite Radar packet age")
    if age < 0 or age > 1:
        return empty

    points = packet.get("radar")
    if points is None:
        raise ValueError("Available Radar packet has no raw radar array")
    points = np.asarray(points, dtype=np.float32)
    if points.ndim != 2 or points.shape[1] != 4:
        raise ValueError("Expected raw Radar [range,azimuth,elevation,velocity]")
    if not np.isfinite(points).all():
        raise ValueError("Non-finite raw Radar points")
    if not len(points):
        return empty

    transform = packet.get("radar_transform")
    if not isinstance(transform, dict):
        raise ValueError("Nonempty Radar packet needs a transform dictionary")
    keys = ("x", "y", "z", "roll", "pitch", "yaw")
    if any(key not in transform for key in keys):
        raise ValueError("Incomplete Radar transform")

    # Collector NPZ convention: [x,y,z,roll,pitch,yaw].
    transform_array = [float(transform[key]) for key in keys]
    return encode_runtime_radar_to_ego(
        points, transform_array, ego_pose,
        available=True, stale=False,
    )
