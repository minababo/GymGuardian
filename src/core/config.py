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


POSE_CONFIG = PoseConfig()
SQUAT_CONFIG = SquatConfig()
