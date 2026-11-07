from __future__ import print_function

import numpy as np


def polar_radar_to_cartesian(radar_points):
    """
    Convert CARLA radar rows from
    [range, azimuth, elevation, radial_velocity] to
    [x, y, z, radial_velocity].
    """
    points = np.asarray(radar_points, dtype=np.float32)

    if points.ndim != 2 or points.shape[1] != 4:
        raise ValueError("radar_points must have shape Nx4")

    if points.shape[0] == 0:
        return np.empty((0, 4), dtype=np.float32)

    distance = points[:, 0]
    azimuth = points[:, 1]
    elevation = points[:, 2]
    velocity = points[:, 3]

    cos_elevation = np.cos(elevation)

    x = distance * cos_elevation * np.cos(azimuth)
    y = distance * cos_elevation * np.sin(azimuth)
    z = distance * np.sin(elevation)

    return np.column_stack(
        (x, y, z, velocity)
    ).astype(np.float32)


def encode_radar_bev(
        radar_points,
        x_range=(-36.0, 36.0),
        y_range=(-12.0, 12.0),
        resolution=0.125,
        density_cap=8.0,
        doppler_cap=20.0):
    """
    Return a float32 tensor [4, H, W]:

        channel 0: normalized log-density
        channel 1: normalized mean signed Doppler
        channel 2: normalized maximum absolute Doppler
        channel 3: occupied-cell mask

    H follows Y (rows) and W follows X (columns).
    Perception consumes channels 0-2. Channel 3 is not a model input.
    """
    x_min, x_max = map(float, x_range)
    y_min, y_max = map(float, y_range)
    resolution = float(resolution)

    if resolution <= 0:
        raise ValueError("resolution must be positive")

    # Tensor layout: [channels, y_rows, x_columns]
    width = int(np.ceil((x_max - x_min) / resolution))
    height = int(np.ceil((y_max - y_min) / resolution))

    output = np.zeros((4, height, width), dtype=np.float32)

    cartesian = polar_radar_to_cartesian(radar_points)

    # Match the exact LiDAR transform used by V2XverseBasedataset:
    # model_x = sensor_y, model_y = -sensor_x
    if cartesian.shape[0] > 0:
        sensor_x = cartesian[:, 0].copy()
        sensor_y = cartesian[:, 1].copy()
        cartesian[:, 0] = sensor_y
        cartesian[:, 1] = -sensor_x

    if cartesian.shape[0] == 0:
        return output

    finite = np.all(np.isfinite(cartesian), axis=1)
    cartesian = cartesian[finite]

    x = cartesian[:, 0]
    y = cartesian[:, 1]
    velocity = cartesian[:, 3]

    row = np.floor((y - y_min) / resolution).astype(np.int64)
    column = np.floor((x - x_min) / resolution).astype(np.int64)

    inside = (
        (row >= 0) & (row < height) &
        (column >= 0) & (column < width)
    )

    row = row[inside]
    column = column[inside]
    velocity = velocity[inside]

    if row.size == 0:
        return output

    count = np.zeros((height, width), dtype=np.float32)
    velocity_sum = np.zeros_like(count)
    max_abs_velocity = np.zeros_like(count)

    np.add.at(count, (row, column), 1.0)
    np.add.at(velocity_sum, (row, column), velocity)
    np.maximum.at(
        max_abs_velocity,
        (row, column),
        np.abs(velocity)
    )

    occupied = count > 0

    output[0] = np.log1p(
        np.minimum(count, density_cap)
    ) / np.log1p(density_cap)

    output[1, occupied] = (
        velocity_sum[occupied] / count[occupied]
    )
    output[1] = np.clip(
        output[1],
        -doppler_cap,
        doppler_cap
    ) / doppler_cap

    output[2] = np.clip(
        max_abs_velocity,
        0.0,
        doppler_cap
    ) / doppler_cap

    output[3, occupied] = 1.0

    return output.astype(np.float32, copy=False)


def load_and_encode_radar(path, **kwargs):
    """
    Load a collector NPZ and encode radar_points into BEV.
    """
    with np.load(str(path), allow_pickle=False) as data:
        packet_available = bool(data["radar_packet_available"])
        stale = bool(data["radar_is_stale"])
        points = data["radar_points"]

    if not packet_available or stale:
        points = np.empty((0, 4), dtype=np.float32)

    return encode_radar_bev(points, **kwargs)


def encode_cartesian_radar_bev(
        cartesian_points,
        x_range=(-36.0, 36.0),
        y_range=(-12.0, 12.0),
        resolution=0.125,
        density_cap=8.0,
        doppler_cap=20.0):
    """
    Encode ego-frame Cartesian radar points [x, y, z, velocity].
    Returns [4, H, W]: density, mean Doppler,
    maximum absolute Doppler, occupancy.
    """
    points = np.asarray(cartesian_points, dtype=np.float32)

    if points.ndim != 2 or points.shape[1] != 4:
        raise ValueError("cartesian_points must have shape Nx4")

    x_min, x_max = map(float, x_range)
    y_min, y_max = map(float, y_range)
    resolution = float(resolution)

    width = int(np.ceil((x_max - x_min) / resolution))
    height = int(np.ceil((y_max - y_min) / resolution))
    output = np.zeros((4, height, width), dtype=np.float32)

    if points.shape[0] == 0:
        return output

    points = points[np.all(np.isfinite(points), axis=1)]

    if points.shape[0] == 0:
        return output

    x = points[:, 0]
    y = points[:, 1]
    velocity = points[:, 3]

    row = np.floor((y - y_min) / resolution).astype(np.int64)
    column = np.floor((x - x_min) / resolution).astype(np.int64)

    inside = (
        (row >= 0) & (row < height) &
        (column >= 0) & (column < width)
    )

    row = row[inside]
    column = column[inside]
    velocity = velocity[inside]

    if row.size == 0:
        return output

    count = np.zeros((height, width), dtype=np.float32)
    velocity_sum = np.zeros_like(count)
    maximum_velocity = np.zeros_like(count)

    np.add.at(count, (row, column), 1.0)
    np.add.at(velocity_sum, (row, column), velocity)
    np.maximum.at(
        maximum_velocity,
        (row, column),
        np.abs(velocity)
    )

    occupied = count > 0

    output[0] = (
        np.log1p(np.minimum(count, density_cap))
        / np.log1p(density_cap)
    )

    output[1, occupied] = (
        velocity_sum[occupied] / count[occupied]
    )
    output[1] = np.clip(
        output[1], -doppler_cap, doppler_cap
    ) / doppler_cap

    output[2] = np.clip(
        maximum_velocity, 0.0, doppler_cap
    ) / doppler_cap

    output[3, occupied] = 1.0
    return output


def load_and_encode_radar_to_ego(path, ego_pose, **kwargs):
    """
    Load RSU Radar, transform radar-local coordinates to world,
    then world coordinates to the Ego model frame.

    ego_pose format: [x, y, z, roll_deg, yaw_deg, pitch_deg].
    """
    with np.load(str(path), allow_pickle=False) as data:
        available = bool(data["radar_packet_available"])
        stale = bool(data["radar_is_stale"])
        points = data["radar_points"]
        radar_transform = data["radar_transform"]

    if not available or stale or points.shape[0] == 0:
        return encode_cartesian_radar_bev(
            np.empty((0, 4), dtype=np.float32),
            **kwargs
        )

    local = polar_radar_to_cartesian(points)

    radar_yaw = np.deg2rad(float(radar_transform[5]))
    cos_r = np.cos(radar_yaw)
    sin_r = np.sin(radar_yaw)

    world_x = (
        float(radar_transform[0])
        + cos_r * local[:, 0]
        - sin_r * local[:, 1]
    )
    world_y = (
        float(radar_transform[1])
        + sin_r * local[:, 0]
        + cos_r * local[:, 1]
    )

    ego_x = float(ego_pose[0])
    ego_y = float(ego_pose[1])
    ego_yaw = np.deg2rad(float(ego_pose[4]))

    dx = world_x - ego_x
    dy = world_y - ego_y

    cos_e = np.cos(ego_yaw)
    sin_e = np.sin(ego_yaw)

    ego_points = np.empty_like(local)
    ego_points[:, 0] = cos_e * dx + sin_e * dy
    ego_points[:, 1] = -sin_e * dx + cos_e * dy
    ego_points[:, 2] = (
        float(radar_transform[2])
        + local[:, 2]
        - float(ego_pose[2])
    )
    ego_points[:, 3] = local[:, 3]

    return encode_cartesian_radar_bev(
        ego_points,
        **kwargs
    )
