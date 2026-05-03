"""Configuration values for the GymGuardian squat coach prototype."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PoseConfig:
    model_complexity: int = 1
    smooth_landmarks: bool = True
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5


@dataclass(frozen=True)
class SquatConfig:
    down_knee_angle: float = 100.0
    up_knee_angle: float = 160.0
    rep_bottom_knee_angle: float = 140.0
    shallow_knee_angle: float = 110.0
    ankle_control_angle: float = 88.0
    torso_lean_angle: float = 34.0
    landmark_visibility_threshold: float = 0.55
    angle_smoothing_window: int = 5
    down_hold_frames: int = 6
    ready_standing_frames: int = 3
    no_pose_reset_frames: int = 4
    min_rep_seconds: float = 0.6


@dataclass(frozen=True)
class CalibrationConfig:
    collection_seconds: float = 12.0
    min_samples: int = 30
    min_movement_range: float = 25.0
    down_margin_ratio: float = 0.12
    shallow_margin_ratio: float = 0.20
    rep_bottom_margin_ratio: float = 0.45
    up_margin_ratio: float = 0.08
    min_down_margin: float = 6.0
    max_down_margin: float = 12.0
    min_shallow_margin: float = 14.0
    max_shallow_margin: float = 25.0
    min_rep_bottom_margin: float = 30.0
    max_rep_bottom_margin: float = 50.0
    min_up_margin: float = 6.0
    max_up_margin: float = 12.0


POSE_CONFIG = PoseConfig()
SQUAT_CONFIG = SquatConfig()
CALIBRATION_CONFIG = CalibrationConfig()
