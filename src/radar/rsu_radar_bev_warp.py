import json
import math
import os

import numpy as np


class RSUToEgoRadarBEVLogger:
    """
    Warp an RSU-local Radar BEV onto an ego-actor-local BEV grid.

    Coordinate convention in both frames:
      x: forward
      y: right
      z: up

    Channel semantics:
      channel 0: normalized point density
      channel 1: mean signed RSU radial velocity [m/s]

    Important:
      Channel 1 remains Doppler relative to the RSU radar after spatial
      warping. It is not converted to ego-relative radial velocity.
    """

    def __init__(self, bev_config, log_root):
        bev_config = bev_config or {}
        warp_config = bev_config.get("ego_warp", {}) or {}

        self.enabled = bool(warp_config.get("enabled", False))

        self.front = float(bev_config.get("front_m", 36.0))
        self.rear = float(bev_config.get("rear_m", 12.0))
        self.left = float(bev_config.get("left_m", 12.0))
        self.right = float(bev_config.get("right_m", 12.0))
        self.resolution = float(
            bev_config.get("resolution_m", 0.25)
        )
        self.max_points_per_cell = float(
            bev_config.get("max_points_per_cell", 5.0)
        )

        self.height = int(
            round((self.front + self.rear) / self.resolution)
        )
        self.width = int(
            round((self.left + self.right) / self.resolution)
        )

        self.save_npz = bool(
            warp_config.get("save_npz", True)
        )
        self.log_subdir = warp_config.get(
            "log_subdir",
            "rsu_radar/bev_ego"
        )

        self.output_dir = None
        self.index_path = None
        self._index_file = None

        if log_root is not None:
            self.output_dir = os.path.join(
                str(log_root),
                self.log_subdir
            )
            self.index_path = os.path.join(
                self.output_dir,
                "radar_bev_ego_index.jsonl"
            )

    def _ensure_output(self):
        if not self.enabled or self.output_dir is None:
            return False

        os.makedirs(self.output_dir, exist_ok=True)

        if self._index_file is None:
            self._index_file = open(
                self.index_path,
                "a",
                buffering=1
            )

        return True

    @staticmethod
    def _transform_to_dict(transform):
        """
        Accept either carla.Transform or a transform dictionary.
        """
        if transform is None:
            return None

        if isinstance(transform, dict):
            return {
                "x": float(transform.get("x", 0.0)),
                "y": float(transform.get("y", 0.0)),
                "z": float(transform.get("z", 0.0)),
                "roll": float(transform.get("roll", 0.0)),
                "pitch": float(transform.get("pitch", 0.0)),
                "yaw": float(transform.get("yaw", 0.0)),
            }

        return {
            "x": float(transform.location.x),
            "y": float(transform.location.y),
            "z": float(transform.location.z),
            "roll": float(transform.rotation.roll),
            "pitch": float(transform.rotation.pitch),
            "yaw": float(transform.rotation.yaw),
        }

    @staticmethod
    def _normalize_yaw_deg(yaw):
        return (float(yaw) + 180.0) % 360.0 - 180.0

    @staticmethod
    def _rotation_matrix(yaw_deg):
        yaw = math.radians(float(yaw_deg))
        cosine = math.cos(yaw)
        sine = math.sin(yaw)

        return np.array([
            [cosine, -sine],
            [sine, cosine],
        ], dtype=np.float64)

    def warp(self,
             rsu_bev,
             point_count,
             rsu_transform,
             ego_transform):
        """
        Forward-warp occupied RSU cells into the ego grid.

        The point count is used as the accumulation weight so that:
          - density can be reconstructed after warping;
          - velocity remains a point-count-weighted mean;
          - interpolation does not create velocity in empty cells.

        Returns:
            ego_bev: float32 array with shape (2, 192, 96)
            ego_point_count: int32 array with shape (192, 96)
            stats: transformation and point-accounting metadata
        """
        rsu_bev = np.asarray(rsu_bev, dtype=np.float32)
        point_count = np.asarray(point_count)

        expected_bev_shape = (2, self.height, self.width)
        expected_count_shape = (self.height, self.width)

        if rsu_bev.shape != expected_bev_shape:
            raise ValueError(
                "Invalid RSU Radar BEV shape: {}; expected {}".format(
                    rsu_bev.shape,
                    expected_bev_shape
                )
            )

        if point_count.shape != expected_count_shape:
            raise ValueError(
                "Invalid Radar point_count shape: {}; expected {}".format(
                    point_count.shape,
                    expected_count_shape
                )
            )

        if not np.all(np.isfinite(rsu_bev)):
            raise ValueError("RSU Radar BEV contains non-finite values")

        rsu_tf = self._transform_to_dict(rsu_transform)
        ego_tf = self._transform_to_dict(ego_transform)

        if rsu_tf is None:
            raise ValueError("RSU radar transform is unavailable")

        if ego_tf is None:
            raise ValueError("Ego transform is unavailable")

        ego_bev = np.zeros(
            expected_bev_shape,
            dtype=np.float32
        )
        ego_point_count = np.zeros(
            expected_count_shape,
            dtype=np.int32
        )

        occupied_rows, occupied_cols = np.nonzero(
            point_count > 0
        )

        source_occupied_cells = int(occupied_rows.size)
        source_points = int(
            np.asarray(point_count, dtype=np.int64).sum()
        )

        rsu_rotation = self._rotation_matrix(rsu_tf["yaw"])
        ego_rotation = self._rotation_matrix(ego_tf["yaw"])

        rsu_translation = np.array([
            rsu_tf["x"],
            rsu_tf["y"],
        ], dtype=np.float64)

        ego_translation = np.array([
            ego_tf["x"],
            ego_tf["y"],
        ], dtype=np.float64)

        # RSU origin represented in the ego actor frame.
        rsu_origin_ego = np.dot(
            ego_rotation.T,
            rsu_translation - ego_translation
        )

        relative_yaw_deg = self._normalize_yaw_deg(
            rsu_tf["yaw"] - ego_tf["yaw"]
        )

        points_outside_ego_bev = 0
        cells_outside_ego_bev = 0

        if source_occupied_cells > 0:
            x_rsu = (
                self.front
                - (occupied_rows.astype(np.float64) + 0.5)
                * self.resolution
            )
            y_rsu = (
                -self.left
                + (occupied_cols.astype(np.float64) + 0.5)
                * self.resolution
            )

            positions_rsu = np.stack(
                [x_rsu, y_rsu],
                axis=0
            )

            positions_world = (
                np.dot(rsu_rotation, positions_rsu)
                + rsu_translation[:, None]
            )

            positions_ego = np.dot(
                ego_rotation.T,
                positions_world - ego_translation[:, None]
            )

            x_ego = positions_ego[0]
            y_ego = positions_ego[1]

            # Small epsilon prevents integer-boundary floating-point
            # errors in identity and exact-cell translation tests.
            epsilon = 1e-6

            ego_rows = np.floor(
                (self.front - x_ego) / self.resolution
                + epsilon
            ).astype(np.int64)

            ego_cols = np.floor(
                (y_ego + self.left) / self.resolution
                + epsilon
            ).astype(np.int64)

            valid = (
                (ego_rows >= 0)
                & (ego_rows < self.height)
                & (ego_cols >= 0)
                & (ego_cols < self.width)
            )

            source_cell_counts = point_count[
                occupied_rows,
                occupied_cols
            ].astype(np.int64)

            source_velocity = rsu_bev[
                1,
                occupied_rows,
                occupied_cols
            ].astype(np.float64)

            points_outside_ego_bev = int(
                source_cell_counts[~valid].sum()
            )
            cells_outside_ego_bev = int(
                np.count_nonzero(~valid)
            )

            valid_rows = ego_rows[valid]
            valid_cols = ego_cols[valid]
            valid_counts = source_cell_counts[valid]
            valid_velocity = source_velocity[valid]

            flat_indices = (
                valid_rows * self.width + valid_cols
            )

            flat_size = self.height * self.width

            accumulated_count = np.bincount(
                flat_indices,
                weights=valid_counts,
                minlength=flat_size
            ).reshape(self.height, self.width)

            accumulated_velocity = np.bincount(
                flat_indices,
                weights=valid_velocity * valid_counts,
                minlength=flat_size
            ).reshape(self.height, self.width)

            ego_point_count = accumulated_count.astype(
                np.int32
            )

            output_occupied = ego_point_count > 0

            ego_bev[0] = np.minimum(
                accumulated_count / self.max_points_per_cell,
                1.0
            ).astype(np.float32)

            ego_bev[1, output_occupied] = (
                accumulated_velocity[output_occupied]
                / accumulated_count[output_occupied]
            ).astype(np.float32)

        points_inside_ego_bev = int(
            ego_point_count.astype(np.int64).sum()
        )
        output_occupied_cells = int(
            np.count_nonzero(ego_point_count)
        )

        occupied_velocity = ego_bev[1][ego_point_count > 0]

        if occupied_velocity.size > 0:
            velocity_min = float(occupied_velocity.min())
            velocity_max = float(occupied_velocity.max())
            max_abs_velocity = float(
                np.max(np.abs(occupied_velocity))
            )
        else:
            velocity_min = 0.0
            velocity_max = 0.0
            max_abs_velocity = 0.0

        stats = {
            "coordinate_frame": "ego_actor_local",
            "source_coordinate_frame": "rsu_radar_local",
            "warped_to_ego": True,
            "planner_connected": False,
            "shape": [
                2,
                self.height,
                self.width
            ],
            "channel_0": "normalized_point_density",
            "channel_1": (
                "mean_signed_rsu_radial_velocity_mps_"
                "warped_to_ego_grid"
            ),
            "velocity_reference": "rsu_radar",
            "warp_method": "count_weighted_forward_splat",
            "source_occupied_cells": source_occupied_cells,
            "output_occupied_cells": output_occupied_cells,
            "source_points": source_points,
            "points_inside_ego_bev": points_inside_ego_bev,
            "points_outside_ego_bev": points_outside_ego_bev,
            "cells_outside_ego_bev": cells_outside_ego_bev,
            "point_balance_valid": bool(
                source_points
                == points_inside_ego_bev
                + points_outside_ego_bev
            ),
            "density_min": float(ego_bev[0].min()),
            "density_max": float(ego_bev[0].max()),
            "occupied_velocity_min_mps": velocity_min,
            "occupied_velocity_max_mps": velocity_max,
            "max_abs_occupied_velocity_mps": max_abs_velocity,
            "all_values_finite": bool(
                np.all(np.isfinite(ego_bev))
            ),
            "empty_cell_velocity_zero": bool(
                np.all(ego_bev[1][ego_point_count == 0] == 0.0)
            ),
            "relative_yaw_deg": float(relative_yaw_deg),
            "rsu_origin_ego": {
                "x": float(rsu_origin_ego[0]),
                "y": float(rsu_origin_ego[1]),
            },
            "rsu_transform": rsu_tf,
            "ego_transform": ego_tf,
        }

        return ego_bev, ego_point_count, stats

    def process_and_log(self,
                        rsu_bev,
                        point_count,
                        rsu_transform,
                        ego_transform,
                        simulation_step,
                        timestamp,
                        ego_vehicle_id,
                        rsu_id,
                        radar_frame,
                        return_arrays=False):
        if not self.enabled:
            return None

        ego_bev, ego_point_count, stats = self.warp(
            rsu_bev=rsu_bev,
            point_count=point_count,
            rsu_transform=rsu_transform,
            ego_transform=ego_transform,
        )

        file_name = (
            "step_{:06d}_ego_{}_rsu_{}_radar_{:06d}.npz"
        ).format(
            int(simulation_step),
            int(ego_vehicle_id),
            int(rsu_id) if rsu_id is not None else -1,
            int(radar_frame) if radar_frame is not None else -1,
        )

        record = {
            "simulation_step": int(simulation_step),
            "timestamp": float(timestamp),
            "ego_vehicle_id": int(ego_vehicle_id),
            "rsu_id": (
                int(rsu_id)
                if rsu_id is not None
                else None
            ),
            "radar_frame": (
                int(radar_frame)
                if radar_frame is not None
                else None
            ),
            "npz_file": file_name if self.save_npz else None,
        }
        record.update(stats)

        if self._ensure_output():
            if self.save_npz:
                np.savez_compressed(
                    os.path.join(self.output_dir, file_name),
                    radar_bev=ego_bev,
                    point_count=ego_point_count,
                    simulation_step=np.int64(simulation_step),
                    timestamp=np.float64(timestamp),
                    ego_vehicle_id=np.int64(ego_vehicle_id),
                    rsu_id=np.int64(
                        rsu_id if rsu_id is not None else -1
                    ),
                    radar_frame=np.int64(
                        radar_frame
                        if radar_frame is not None
                        else -1
                    ),
                    relative_yaw_deg=np.float32(
                        stats["relative_yaw_deg"]
                    ),
                    rsu_origin_ego_x=np.float32(
                        stats["rsu_origin_ego"]["x"]
                    ),
                    rsu_origin_ego_y=np.float32(
                        stats["rsu_origin_ego"]["y"]
                    ),
                    source_points=np.int64(
                        stats["source_points"]
                    ),
                    points_inside_ego_bev=np.int64(
                        stats["points_inside_ego_bev"]
                    ),
                    points_outside_ego_bev=np.int64(
                        stats["points_outside_ego_bev"]
                    ),
                )

            self._index_file.write(
                json.dumps(record, sort_keys=True) + "\n"
            )
            self._index_file.flush()

        if return_arrays:
            velocity_sum = np.ascontiguousarray(
                ego_point_count.astype(np.float32)
                * ego_bev[1].astype(np.float32),
                dtype=np.float32
            )

            return {
                "record": record,
                "radar_bev": ego_bev,
                "point_count": ego_point_count,
                "velocity_sum": velocity_sum,
            }

        return record

    def close(self):
        if self._index_file is not None:
            self._index_file.flush()
            self._index_file.close()
            self._index_file = None
