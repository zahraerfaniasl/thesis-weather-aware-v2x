import json
import math
import os

import numpy as np
import carla

from srunner.scenariomanager.carla_data_provider import CarlaDataProvider


class IdealRSURadarOracle:
    """
    Ideal RSU-mounted radar oracle used only for logging.

    Stage 1 assumptions:
      - no measurement noise
      - no latency
      - no packet loss
      - no probabilistic detection
      - no occlusion filtering
      - no safety or control override

    All radar quantities are computed relative to the transform of the
    actual spawned RSU reference sensor.
    """

    def __init__(self, config, log_root):
        self.config = config or {}
        self.enabled = bool(self.config.get("enabled", False))

        self.max_range = float(
            self.config.get("max_range", 100.0)
        )
        self.horizontal_fov_deg = float(
            self.config.get("horizontal_fov_deg", 360.0)
        )
        self.inactive_z_threshold = float(
            self.config.get("inactive_z_threshold", -50.0)
        )

        log_subdir = self.config.get(
            "log_subdir",
            "radar_oracle"
        )

        self.log_dir = None
        self.log_path = None
        self._log_file = None

        if log_root is not None:
            self.log_dir = os.path.join(str(log_root), log_subdir)
            self.log_path = os.path.join(
                self.log_dir,
                "ideal_rsu_radar.jsonl"
            )

        # Exact CARLA actor IDs registered by RouteScenario.
        self._targets = {}

        # Used only for logging first detection.
        self._first_detection_time = {}

        safety_config = self.config.get("safety_override", {})

        self.safety_enabled = bool(
            safety_config.get("enabled", False)
        )
        self.prediction_horizon_s = float(
            safety_config.get("prediction_horizon_s", 4.0)
        )
        self.longitudinal_margin_m = float(
            safety_config.get("longitudinal_margin_m", 1.0)
        )
        self.lateral_margin_m = float(
            safety_config.get("lateral_margin_m", 0.5)
        )
        self.override_brake = float(
            safety_config.get("brake", 1.0)
        )

        self._safety_log_file = None
        self._first_override_time = {}


    def register_target(self,
                        ego_vehicle_id,
                        actor_id,
                        scenario_name,
                        route_var_name=None,
                        blocker_actor_id=None):
        """
        Register the exact actor created by the scenario instance.
        """
        if not self.enabled:
            return

        actor_id = int(actor_id)

        self._targets[actor_id] = {
            "ego_vehicle_id": int(ego_vehicle_id),
            "actor_id": actor_id,
            "scenario_name": str(scenario_name),
            "route_var_name": route_var_name,
            "blocker_actor_id": (
                int(blocker_actor_id)
                if blocker_actor_id is not None
                else None
            ),
        }

        print(
            "[RSU Radar Oracle] registered target: "
            "ego={}, scenario={}, actor_id={}, blocker_actor_id={}".format(
                ego_vehicle_id,
                scenario_name,
                actor_id,
                blocker_actor_id
            )
        )

    def _ensure_log_file(self):
        if not self.enabled:
            return False

        if self.log_path is None:
            return False

        if self._log_file is None:
            os.makedirs(self.log_dir, exist_ok=True)
            self._log_file = open(
                self.log_path,
                "a",
                buffering=1
            )

        return True

    @staticmethod
    def _copy_location(location):
        return carla.Location(
            x=location.x,
            y=location.y,
            z=location.z
        )

    @classmethod
    def _get_actor_bbox_center_world(cls, actor):
        """
        Return the target bounding-box center in CARLA world coordinates.
        """
        actor_transform = actor.get_transform()
        center_world = cls._copy_location(
            actor.bounding_box.location
        )

        # CARLA 0.9.10 transforms the supplied Location in-place.
        actor_transform.transform(center_world)
        return center_world

    @staticmethod
    def _world_point_to_sensor(point_world, sensor_transform):
        """
        Transform a world-coordinate point into the RSU sensor frame.
        """
        inverse_matrix = np.asarray(
            sensor_transform.get_inverse_matrix(),
            dtype=np.float64
        )

        point_h = np.array([
            point_world.x,
            point_world.y,
            point_world.z,
            1.0
        ], dtype=np.float64)

        return inverse_matrix.dot(point_h)[:3]

    @staticmethod
    def _radial_velocity(target,
                         target_center_world,
                         sensor_transform,
                         sensor_velocity):
        """
        Compute target relative velocity projected onto the RSU line of sight.

        Positive value means increasing target-to-RSU range.
        Negative value means approaching the RSU.
        """
        sensor_location = sensor_transform.location

        los_world = np.array([
            target_center_world.x - sensor_location.x,
            target_center_world.y - sensor_location.y,
            target_center_world.z - sensor_location.z
        ], dtype=np.float64)

        los_norm = np.linalg.norm(los_world)
        if los_norm < 1e-6:
            return 0.0

        los_unit = los_world / los_norm

        target_velocity = target.get_velocity()
        target_velocity_np = np.array([
            target_velocity.x,
            target_velocity.y,
            target_velocity.z
        ], dtype=np.float64)

        if sensor_velocity is None:
            sensor_velocity_np = np.zeros(3, dtype=np.float64)
        else:
            sensor_velocity_np = np.array([
                sensor_velocity.x,
                sensor_velocity.y,
                sensor_velocity.z
            ], dtype=np.float64)

        relative_velocity = (
            target_velocity_np - sensor_velocity_np
        )

        return float(np.dot(relative_velocity, los_unit))

    def _measure_target(self,
                        target_info,
                        sensor_transform,
                        sensor_velocity,
                        timestamp):
        world = CarlaDataProvider.get_world()
        actor_id = target_info["actor_id"]

        target = world.get_actors().find(actor_id)

        measurement = dict(target_info)
        measurement.update({
            "target_alive": False,
            "target_active": False,
            "detected": False,
            "detection_probability": None,
            "occluded": None,
            "range_m": None,
            "azimuth_deg": None,
            "elevation_deg": None,
            "radial_velocity_mps": None,
            "target_world": None,
            "target_sensor": None,
            "first_detection": False,
            "first_detection_time": self._first_detection_time.get(
                actor_id
            ),
        })

        if target is None or not target.is_alive:
            measurement["status"] = "target_not_alive"
            return measurement

        measurement["target_alive"] = True

        target_center_world = (
            self._get_actor_bbox_center_world(target)
        )

        measurement["target_world"] = {
            "x": float(target_center_world.x),
            "y": float(target_center_world.y),
            "z": float(target_center_world.z),
        }

        # STAGE9B_TARGET_KINEMATICS_V1
        target_velocity = target.get_velocity()
        target_extent = target.bounding_box.extent

        measurement["target_type_id"] = str(target.type_id)
        measurement["target_velocity_world"] = {
            "x": float(target_velocity.x),
            "y": float(target_velocity.y),
            "z": float(target_velocity.z),
        }
        measurement["target_bbox_extent"] = {
            "x": float(target_extent.x),
            "y": float(target_extent.y),
            "z": float(target_extent.z),
        }

        # Scenario actors are initially stored below the map.
        if target_center_world.z < self.inactive_z_threshold:
            measurement["status"] = "target_inactive"
            return measurement

        measurement["target_active"] = True

        target_sensor = self._world_point_to_sensor(
            target_center_world,
            sensor_transform
        )

        x_rsu = float(target_sensor[0])
        y_rsu = float(target_sensor[1])
        z_rsu = float(target_sensor[2])

        range_m = float(np.linalg.norm(target_sensor))
        horizontal_range = math.hypot(x_rsu, y_rsu)

        azimuth_deg = math.degrees(
            math.atan2(y_rsu, x_rsu)
        )
        elevation_deg = math.degrees(
            math.atan2(z_rsu, horizontal_range)
        )

        radial_velocity = self._radial_velocity(
            target,
            target_center_world,
            sensor_transform,
            sensor_velocity
        )

        measurement["target_sensor"] = {
            "x": x_rsu,
            "y": y_rsu,
            "z": z_rsu,
        }
        measurement["range_m"] = range_m
        measurement["azimuth_deg"] = azimuth_deg
        measurement["elevation_deg"] = elevation_deg
        measurement["radial_velocity_mps"] = radial_velocity

        in_range = range_m <= self.max_range

        if self.horizontal_fov_deg >= 360.0:
            in_horizontal_fov = True
        else:
            in_horizontal_fov = (
                abs(azimuth_deg)
                <= self.horizontal_fov_deg / 2.0
            )

        detected = bool(in_range and in_horizontal_fov)
        measurement["detected"] = detected
        measurement["detection_probability"] = (
            1.0 if detected else 0.0
        )


        if not in_range:
            measurement["status"] = "out_of_range"
        elif not in_horizontal_fov:
            measurement["status"] = "out_of_fov"
        else:
            measurement["status"] = "detected"

        if detected and actor_id not in self._first_detection_time:
            self._first_detection_time[actor_id] = float(timestamp)
            measurement["first_detection"] = True
            measurement["first_detection_time"] = float(timestamp)

        return measurement


    @staticmethod
    def _sensor_point_to_world(sensor_point, sensor_transform):
        matrix = np.asarray(
            sensor_transform.get_matrix(),
            dtype=np.float64
        )

        point_sensor = np.array([
            float(sensor_point["x"]),
            float(sensor_point["y"]),
            float(sensor_point["z"]),
            1.0,
        ], dtype=np.float64)

        point_world = np.dot(matrix, point_sensor)
        return point_world[:3]


    @staticmethod
    def _relative_velocity_in_ego_frame(ego_actor, target_actor):
        ego_velocity = ego_actor.get_velocity()
        target_velocity = target_actor.get_velocity()

        relative_world = np.array([
            target_velocity.x - ego_velocity.x,
            target_velocity.y - ego_velocity.y,
            target_velocity.z - ego_velocity.z,
        ], dtype=np.float64)

        ego_inverse = np.asarray(
            ego_actor.get_transform().get_inverse_matrix(),
            dtype=np.float64
        )

        return np.dot(ego_inverse[:3, :3], relative_world)


    @staticmethod
    def _axis_overlap_interval(position, velocity, limit, horizon):
        epsilon = 1e-6

        position = float(position)
        velocity = float(velocity)
        limit = float(limit)
        horizon = float(horizon)

        if abs(velocity) < epsilon:
            if abs(position) <= limit:
                return 0.0, horizon
            return None

        t1 = (-limit - position) / velocity
        t2 = (limit - position) / velocity

        start = max(0.0, min(t1, t2))
        end = min(horizon, max(t1, t2))

        if start > end:
            return None

        return start, end


    def evaluate_safety(self, ego_actor, oracle_packet):
        result = {
            "override": False,
            "reason": "no_risk",
            "actor_id": None,
            "predicted_collision_time_s": None,
            "target_position_ego": None,
            "relative_velocity_ego": None,
            "velocity_source": "target_actor_ground_truth",
        }

        if not self.safety_enabled:
            result["reason"] = "safety_disabled"
            return result

        if ego_actor is None or not ego_actor.is_alive:
            result["reason"] = "ego_unavailable"
            return result

        if oracle_packet is None:
            result["reason"] = "oracle_packet_unavailable"
            return result

        sensor_transform = oracle_packet.get("sensor_transform")
        record = oracle_packet.get("record", {})

        if sensor_transform is None:
            result["reason"] = "rsu_transform_unavailable"
            return result

        measurements = record.get("measurements", [])
        world = ego_actor.get_world()

        best_risk = None

        for measurement in measurements:
            if not measurement.get("detected", False):
                continue

            target_sensor = measurement.get("target_sensor")
            actor_id = measurement.get("actor_id")

            if target_sensor is None or actor_id is None:
                continue

            target_actor = world.get_actor(int(actor_id))

            if target_actor is None or not target_actor.is_alive:
                continue

            target_world = self._sensor_point_to_world(
                target_sensor,
                sensor_transform
            )

            ego_inverse = np.asarray(
                ego_actor.get_transform().get_inverse_matrix(),
                dtype=np.float64
            )

            target_homogeneous = np.array([
                target_world[0],
                target_world[1],
                target_world[2],
                1.0,
            ], dtype=np.float64)

            target_ego = np.dot(
                ego_inverse,
                target_homogeneous
            )[:3]

            ego_bbox_location = ego_actor.bounding_box.location
            relative_position = np.array([
                target_ego[0] - ego_bbox_location.x,
                target_ego[1] - ego_bbox_location.y,
                target_ego[2] - ego_bbox_location.z,
            ], dtype=np.float64)

            relative_velocity = (
                self._relative_velocity_in_ego_frame(
                    ego_actor,
                    target_actor
                )
            )

            ego_extent = ego_actor.bounding_box.extent
            target_extent = target_actor.bounding_box.extent

            longitudinal_limit = (
                float(ego_extent.x)
                + float(target_extent.x)
                + self.longitudinal_margin_m
            )

            lateral_limit = (
                float(ego_extent.y)
                + float(target_extent.y)
                + self.lateral_margin_m
            )

            x_interval = self._axis_overlap_interval(
                relative_position[0],
                relative_velocity[0],
                longitudinal_limit,
                self.prediction_horizon_s,
            )

            y_interval = self._axis_overlap_interval(
                relative_position[1],
                relative_velocity[1],
                lateral_limit,
                self.prediction_horizon_s,
            )

            if x_interval is None or y_interval is None:
                continue

            overlap_start = max(x_interval[0], y_interval[0])
            overlap_end = min(x_interval[1], y_interval[1])

            if overlap_start > overlap_end:
                continue

            candidate = {
                "override": True,
                "reason": "predicted_footprint_overlap",
                "actor_id": int(actor_id),
                "predicted_collision_time_s": float(overlap_start),
                "target_position_ego": {
                    "x": float(relative_position[0]),
                    "y": float(relative_position[1]),
                    "z": float(relative_position[2]),
                },
                "relative_velocity_ego": {
                    "x": float(relative_velocity[0]),
                    "y": float(relative_velocity[1]),
                    "z": float(relative_velocity[2]),
                },
                "velocity_source": "target_actor_ground_truth",
            }

            if (
                best_risk is None
                or candidate["predicted_collision_time_s"]
                < best_risk["predicted_collision_time_s"]
            ):
                best_risk = candidate

        if best_risk is not None:
            return best_risk

        return result


    def observe_and_log(self,
                        ego_vehicle_id,
                        simulation_step,
                        timestamp,
                        rsu_unit,
                        ego_actor=None):
        """
        Produce and log ideal measurements for one RSU.

        This method does not return or modify any vehicle control.
        """
        if not self.enabled:
            return None

        sensor_transform = None
        sensor_velocity = None
        sensor_transform_source = None

        if rsu_unit is not None:
            sensor_transform = (
                rsu_unit.get_reference_sensor_transform()
            )
            sensor_transform_source = (
                rsu_unit.get_reference_sensor_transform_source()
            )
            sensor_velocity = (
                rsu_unit.get_reference_sensor_velocity()
            )


        record = {
            "simulation_step": int(simulation_step),
            "timestamp": float(timestamp),
            "ego_vehicle_id": int(ego_vehicle_id),
            "ego_actor_id": (
                int(ego_actor.id)
                if ego_actor is not None and ego_actor.is_alive
                else None
            ),
            "rsu_id": (
                int(rsu_unit.id)
                if rsu_unit is not None
                else None
            ),
            "rsu_available": sensor_transform is not None,
            "rsu_transform_source": sensor_transform_source,
            "rsu_transform": None,
            "measurements": [],
        }

        if sensor_transform is not None:
            record["rsu_transform"] = {
                "x": float(sensor_transform.location.x),
                "y": float(sensor_transform.location.y),
                "z": float(sensor_transform.location.z),
                "roll": float(sensor_transform.rotation.roll),
                "pitch": float(sensor_transform.rotation.pitch),
                "yaw": float(sensor_transform.rotation.yaw),
            }

            for target_info in self._targets.values():
                if (
                    target_info["ego_vehicle_id"]
                    != int(ego_vehicle_id)
                ):
                    continue

                measurement = self._measure_target(
                    target_info,
                    sensor_transform,
                    sensor_velocity,
                    timestamp
                )
                record["measurements"].append(measurement)

        if self._ensure_log_file():
            self._log_file.write(
                json.dumps(record, sort_keys=True) + "\n"
            )
            self._log_file.flush()

            # sensor_transform فقط برای محاسبه safety در همین tick استفاده می‌شود
            # و داخل JSONL ذخیره نمی‌شود.
            return {
                "record": record,
                "sensor_transform": sensor_transform,
            }
        
    def _ensure_safety_log_file(self):
        if self._safety_log_file is not None:
            return

        if self.log_path is None:
            return

        safety_log_path = os.path.join(
            os.path.dirname(self.log_path),
            "ideal_rsu_safety.jsonl"
        )

        self._safety_log_file = open(
            safety_log_path,
            "a",
            buffering=1
        )


    def apply_safety_override(self,
                              ego_vehicle_id,
                              ego_actor,
                              controls,
                              oracle_packet,
                              timestamp,
                              simulation_step):
        safety = self.evaluate_safety(
            ego_actor,
            oracle_packet
        )

        control = None

        if controls is not None:
            try:
                control = controls[ego_vehicle_id]
            except (KeyError, IndexError, TypeError):
                control = None

        original_control = None
        applied_control = None

        if control is not None:
            original_control = {
                "throttle": float(control.throttle),
                "brake": float(control.brake),
                "steer": float(control.steer),
            }

            if safety["override"]:
                control.throttle = 0.0
                control.brake = max(
                    float(control.brake),
                    self.override_brake
                )

                if (
                    ego_vehicle_id
                    not in self._first_override_time
                ):
                    self._first_override_time[
                        ego_vehicle_id
                    ] = float(timestamp)

            applied_control = {
                "throttle": float(control.throttle),
                "brake": float(control.brake),
                "steer": float(control.steer),
            }

        safety_record = {
            "timestamp": float(timestamp),
            "simulation_step": int(simulation_step),
            "ego_vehicle_id": int(ego_vehicle_id),
            "ego_actor_id": (
                int(ego_actor.id)
                if ego_actor is not None
                else None
            ),
            "override": bool(safety["override"]),
            "reason": safety["reason"],
            "actor_id": safety["actor_id"],
            "predicted_collision_time_s": (
                safety["predicted_collision_time_s"]
            ),
            "target_position_ego": (
                safety["target_position_ego"]
            ),
            "relative_velocity_ego": (
                safety["relative_velocity_ego"]
            ),
            "velocity_source": safety["velocity_source"],
            "first_override_time": (
                self._first_override_time.get(
                    ego_vehicle_id
                )
            ),
            "original_control": original_control,
            "applied_control": applied_control,
        }

        self._ensure_safety_log_file()

        if self._safety_log_file is not None:
            self._safety_log_file.write(
                json.dumps(safety_record, sort_keys=True)
                + "\n"
            )
            self._safety_log_file.flush()

        return controls


    def close(self):
        if self._log_file is not None:
            self._log_file.flush()
            self._log_file.close()
            self._log_file = None

        if self._safety_log_file is not None:
            self._safety_log_file.flush()
            self._safety_log_file.close()
            self._safety_log_file = None

