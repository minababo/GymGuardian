"""Configuration values for the GymGuardian MVP."""

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


POSE_CONFIG = PoseConfig()
SQUAT_CONFIG = SquatConfig()
