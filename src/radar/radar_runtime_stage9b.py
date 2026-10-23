"""In-memory equivalent of the existing offline Radar encoder."""
import numpy as np
from opencood.data_utils.radar.radar_bev import (
    polar_radar_to_cartesian,
    encode_cartesian_radar_bev,
)

def encode_runtime_radar_to_ego(
        radar_points, radar_transform, ego_pose,
        available=True, stale=False, **kwargs):
    """
    Preserve the existing offline convention, including yaw-only rotation.
    radar_transform: same six-value ordering as the collector NPZ;
                     yaw is element 5.
    ego_pose: [x, y, z, roll, yaw, pitch], degrees.
    Returns four channels; Perception consumes the first three.
    """
    empty = np.empty((0, 4), dtype=np.float32)
    if not available or stale:
        return encode_cartesian_radar_bev(empty, **kwargs)

    points = np.asarray(radar_points, dtype=np.float32)
    if points.ndim != 2 or points.shape[1] != 4:
        raise ValueError("radar_points must have shape Nx4")
    if not len(points):
        return encode_cartesian_radar_bev(empty, **kwargs)

    transform = np.asarray(radar_transform, dtype=np.float64)
    pose = np.asarray(ego_pose, dtype=np.float64)
    if transform.shape != (6,) or pose.shape != (6,):
        raise ValueError("Expected two six-value poses")
    if not np.isfinite(transform).all() or not np.isfinite(pose).all():
        raise ValueError("Non-finite pose")
    if not np.isfinite(points).all():
        raise ValueError("Non-finite Radar packet")

    local = polar_radar_to_cartesian(points)
    yaw = np.deg2rad(float(transform[5]))
    cr, sr = np.cos(yaw), np.sin(yaw)
    world_x = float(transform[0]) + cr * local[:, 0] - sr * local[:, 1]
    world_y = float(transform[1]) + sr * local[:, 0] + cr * local[:, 1]

    dx = world_x - float(pose[0])
    dy = world_y - float(pose[1])
    yaw = np.deg2rad(float(pose[4]))
    ce, se = np.cos(yaw), np.sin(yaw)

    ego = np.empty_like(local)
    ego[:, 0] = ce * dx + se * dy
    ego[:, 1] = -se * dx + ce * dy
    ego[:, 2] = float(transform[2]) + local[:, 2] - float(pose[2])
    ego[:, 3] = local[:, 3]
    return encode_cartesian_radar_bev(ego, **kwargs)
