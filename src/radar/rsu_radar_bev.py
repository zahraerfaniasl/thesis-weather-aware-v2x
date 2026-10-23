import json
import os

import numpy as np


class RSURadarBEVLogger(object):
    """
    Build and log a two-channel Radar BEV in the local RSU frame.

    Input radar column layout:


$$
range_m, azimuth_rad, elevation_rad, radial_velocity_mps
$$



    Output radar_bev layout:
        channel 0: normalized point density
        channel 1: mean signed radial velocity in m/s

    Coordinate convention:
        x: RSU forward
        y: RSU right
        z: RSU up

    Grid convention:
        row 0: front edge
        increasing row: toward the rear
        column 0: left edge
        increasing column: toward the right
    """

    def __init__(self, config, log_root):
        self.config = config or {}
        self.enabled = bool(self.config.get("enabled", False))

        self.front_m = float(
            self.config.get("front_m", 36.0)
        )
        self.rear_m = float(
            self.config.get("rear_m", 12.0)
        )
        self.left_m = float(
            self.config.get("left_m", 12.0)
        )
        self.right_m = float(
            self.config.get("right_m", 12.0)
        )
        self.resolution_m = float(
            self.config.get("resolution_m", 0.25)
        )

        self.max_points_per_cell = float(
            self.config.get("max_points_per_cell", 5.0)
        )
        self.save_npz = bool(
            self.config.get("save_npz", True)
        )

        if self.resolution_m <= 0:
            raise ValueError(
                "RSU Radar BEV resolution_m must be positive"
            )

        if self.max_points_per_cell <= 0:
            raise ValueError(
                "RSU Radar BEV max_points_per_cell must be positive"
            )

        self.height = int(round(
            (self.front_m + self.rear_m)
            / self.resolution_m
        ))
        self.width = int(round(
            (self.left_m + self.right_m)
            / self.resolution_m
        ))

        # The first paper-facing representation is fixed to 2x192x96.
        if self.height != 192 or self.width != 96:
            raise ValueError(
                "Expected Radar BEV shape 2x192x96, got 2x{}x{}. "
                "Check front/rear/left/right/resolution.".format(
                    self.height,
                    self.width
                )
            )

        log_subdir = self.config.get(
            "log_subdir",
            "rsu_radar/bev_rsu"
        )

        self.log_dir = None
        self.index_path = None
        self._index_file = None

        if log_root is not None:
            self.log_dir = os.path.join(
                str(log_root),
                str(log_subdir)
            )
            self.index_path = os.path.join(
                self.log_dir,
                "radar_bev_index.jsonl"
            )

    def _ensure_output(self):
        if not self.enabled:
            return False

        if self.log_dir is None:
            return False

        os.makedirs(self.log_dir, exist_ok=True)

        if self._index_file is None:
            self._index_file = open(
                self.index_path,
                "a",
                buffering=1
            )

        return True

    def build(self, radar_points):
        """
        Build the two-channel BEV from filtered results["radar"].

        Parameters
        ----------
        radar_points : numpy.ndarray
            Shape N x 4:


$$
range, azimuth, elevation, radial_velocity
$$



        Returns
        -------
        radar_bev : numpy.ndarray
            float32, shape [2, 192, 96]

        point_count : numpy.ndarray
            int32, shape [192, 96], retained only for audit.

        stats : dict
            Numerical audit information.
        """
        radar_bev = np.zeros(
            (2, self.height, self.width),
            dtype=np.float32
        )
        point_count = np.zeros(
            (self.height, self.width),
            dtype=np.int32
        )

        if radar_points is None:
            radar_points = np.empty((0, 4), dtype=np.float32)

        radar_points = np.asarray(
            radar_points,
            dtype=np.float32
        )

        if radar_points.size == 0:
            radar_points = radar_points.reshape(0, 4)

        if radar_points.ndim != 2 or radar_points.shape[1] != 4:
            raise ValueError(
                "Filtered RSU radar must have shape N x 4, got {}".format(
                    radar_points.shape
                )
            )

        input_points = int(radar_points.shape[0])

        if input_points == 0:
            stats = {
                "input_points": 0,
                "finite_points": 0,
                "points_in_bev": 0,
                "points_outside_bev": 0,
                "occupied_cells": 0,
                "density_min": 0.0,
                "density_max": 0.0,
                "mean_velocity_min_mps": 0.0,
                "mean_velocity_max_mps": 0.0,
            }
            return radar_bev, point_count, stats

        finite_mask = np.all(
            np.isfinite(radar_points),
            axis=1
        )
        radar_points = radar_points[finite_mask]
        finite_points = int(radar_points.shape[0])

        if finite_points == 0:
            stats = {
                "input_points": input_points,
                "finite_points": 0,
                "points_in_bev": 0,
                "points_outside_bev": input_points,
                "occupied_cells": 0,
                "density_min": 0.0,
                "density_max": 0.0,
                "mean_velocity_min_mps": 0.0,
                "mean_velocity_max_mps": 0.0,
            }
            return radar_bev, point_count, stats

        ranges = radar_points[:, 0]
        azimuth = radar_points[:, 1]
        elevation = radar_points[:, 2]
        radial_velocity = radar_points[:, 3]

        horizontal_range = ranges * np.cos(elevation)

        # CARLA Radar local coordinates:
        # x forward, y right, z up.
        x = horizontal_range * np.cos(azimuth)
        y = horizontal_range * np.sin(azimuth)

        row = np.floor(
            (self.front_m - x) / self.resolution_m
        ).astype(np.int64)

        col = np.floor(
            (y + self.left_m) / self.resolution_m
        ).astype(np.int64)

        inside_mask = (
            (x <= self.front_m)
            & (x > -self.rear_m)
            & (y >= -self.left_m)
            & (y < self.right_m)
            & (row >= 0)
            & (row < self.height)
            & (col >= 0)
            & (col < self.width)
        )

        row = row[inside_mask]
        col = col[inside_mask]
        radial_velocity = radial_velocity[inside_mask]

        points_in_bev = int(row.shape[0])
        points_outside_bev = int(
            input_points - points_in_bev
        )

        if points_in_bev > 0:
            flat_index = row * self.width + col
            flat_size = self.height * self.width

            count_flat = np.bincount(
                flat_index,
                minlength=flat_size
            ).astype(np.int32)

            velocity_sum_flat = np.bincount(
                flat_index,
                weights=radial_velocity.astype(np.float64),
                minlength=flat_size
            )

            point_count = count_flat.reshape(
                self.height,
                self.width
            )

            velocity_sum = velocity_sum_flat.reshape(
                self.height,
                self.width
            )

            occupied_mask = point_count > 0

            density = np.minimum(
                point_count.astype(np.float32)
                / self.max_points_per_cell,
                1.0
            )

            mean_velocity = np.zeros(
                (self.height, self.width),
                dtype=np.float32
            )

            mean_velocity[occupied_mask] = (
                velocity_sum[occupied_mask]
                / point_count[occupied_mask]
            ).astype(np.float32)

            radar_bev[0] = density
            radar_bev[1] = mean_velocity

            occupied_velocity = mean_velocity[occupied_mask]
            velocity_min = float(
                np.min(occupied_velocity)
            )
            velocity_max = float(
                np.max(occupied_velocity)
            )
            occupied_cells = int(
                np.count_nonzero(occupied_mask)
            )
        else:
            velocity_min = 0.0
            velocity_max = 0.0
            occupied_cells = 0

        stats = {
            "input_points": input_points,
            "finite_points": finite_points,
            "points_in_bev": points_in_bev,
            "points_outside_bev": points_outside_bev,
            "occupied_cells": occupied_cells,
            "density_min": float(np.min(radar_bev[0])),
            "density_max": float(np.max(radar_bev[0])),
            "mean_velocity_min_mps": velocity_min,
            "mean_velocity_max_mps": velocity_max,
        }

        return radar_bev, point_count, stats

    def process_and_log(self,
                        radar_points,
                        simulation_step,
                        timestamp,
                        ego_vehicle_id,
                        rsu_id=None,
                        radar_frame=None,
                        return_arrays=False):
        """
        Build and save one RSU-local Radar BEV.

        This method has no connection to the Planner.
        """
        if not self.enabled:
            return None

        radar_bev, point_count, stats = self.build(
            radar_points
        )

        if not self._ensure_output():
            if return_arrays:
                return {
                    "record": stats,
                    "radar_bev": radar_bev,
                    "point_count": point_count,
                }
            return stats

        radar_frame_for_name = (
            int(radar_frame)
            if radar_frame is not None
            else -1
        )

        rsu_id_for_name = (
            int(rsu_id)
            if rsu_id is not None
            else -1
        )

        filename = (
            "step_{:06d}_ego_{}_rsu_{}_radar_{:06d}.npz"
        ).format(
            int(simulation_step),
            int(ego_vehicle_id),
            rsu_id_for_name,
            radar_frame_for_name
        )

        npz_path = os.path.join(
            self.log_dir,
            filename
        )

        if self.save_npz:
            np.savez_compressed(
                npz_path,
                radar_bev=radar_bev,
                point_count=point_count,
                simulation_step=np.int64(simulation_step),
                timestamp=np.float64(timestamp),
                ego_vehicle_id=np.int32(ego_vehicle_id),
                rsu_id=np.int64(rsu_id_for_name),
                radar_frame=np.int64(radar_frame_for_name),
                front_m=np.float32(self.front_m),
                rear_m=np.float32(self.rear_m),
                left_m=np.float32(self.left_m),
                right_m=np.float32(self.right_m),
                resolution_m=np.float32(self.resolution_m),
                max_points_per_cell=np.float32(
                    self.max_points_per_cell
                ),
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
            "coordinate_frame": "rsu_local",
            "warped_to_ego": False,
            "planner_connected": False,
            "shape": [2, self.height, self.width],
            "channels": [
                "normalized_density",
                "mean_signed_radial_velocity_mps"
            ],
            "npz_file": (
                filename if self.save_npz else None
            ),
        }
        record.update(stats)

        self._index_file.write(
            json.dumps(record, sort_keys=True) + "\n"
        )
        self._index_file.flush()


        # This summary can also be attached to raw_radar.jsonl.
        
        
        if return_arrays:
            return {
                "record": record,
                "radar_bev": radar_bev,
                "point_count": point_count,
            }

        return record


    def close(self):
        if self._index_file is not None:
            self._index_file.flush()
            self._index_file.close()
            self._index_file = None
