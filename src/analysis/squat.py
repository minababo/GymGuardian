"""Squat state classification and rep counting for MVP (Tasks Pose Landmarker result)."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Optional

from core.config import SQUAT_CONFIG


@dataclass(frozen=True)
class SquatState:
    label: str
    knee_angle: Optional[float]


class SquatStateAnalyzer:
    """Classify a squat as standing, down, or transition using knee angles."""

    def classify(self, pose_result) -> SquatState:
        # pose_result.pose_landmarks -> list of poses; each pose -> list of landmarks
        if pose_result is None or not getattr(pose_result, "pose_landmarks", None):
            return SquatState(label="no_pose", knee_angle=None)
        if len(pose_result.pose_landmarks) == 0:
            return SquatState(label="no_pose", knee_angle=None)

        landmarks = pose_result.pose_landmarks[0]

        # MediaPipe Tasks pose landmarks use indices aligned with BlazePose landmark order.
        # Key indices we need (BlazePose):
        # 23 left hip, 25 left knee, 27 left ankle
        # 24 right hip, 26 right knee, 28 right ankle
        left = self._knee_angle_if_visible(landmarks, 23, 25, 27)
        right = self._knee_angle_if_visible(landmarks, 24, 26, 28)

        angle = self._average_angle([left, right])
        if angle is None:
            return SquatState(label="no_pose", knee_angle=None)

        if angle <= SQUAT_CONFIG.down_knee_angle:
            return SquatState(label="down", knee_angle=angle)
        if angle >= SQUAT_CONFIG.up_knee_angle:
            return SquatState(label="standing", knee_angle=angle)

        return SquatState(label="transition", knee_angle=angle)

    def _knee_angle_if_visible(
        self, landmarks, hip_i, knee_i, ankle_i
    ) -> Optional[float]:
        hip = landmarks[hip_i]
        knee = landmarks[knee_i]
        ankle = landmarks[ankle_i]

        # Tasks landmarks may include visibility/presence depending on model; be defensive.
        vis = [
            getattr(hip, "visibility", 1.0),
            getattr(knee, "visibility", 1.0),
            getattr(ankle, "visibility", 1.0),
        ]
        if min(vis) < 0.5:
            return None

        return _angle_degrees(
            (hip.x, hip.y),
            (knee.x, knee.y),
            (ankle.x, ankle.y),
        )

    @staticmethod
    def _average_angle(values: Iterable[Optional[float]]) -> Optional[float]:
        valid = [v for v in values if v is not None]
        if not valid:
            return None
        return sum(valid) / len(valid)


def _angle_degrees(a, b, c) -> float:
    """Return angle at point b (in degrees) for triangle a-b-c using 2D coords."""
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])

    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.hypot(ba[0], ba[1])
    mag_bc = math.hypot(bc[0], bc[1])
    if mag_ba == 0 or mag_bc == 0:
        return 0.0

    cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


@dataclass(frozen=True)
class RepCounterUpdate:
    rep_started: bool = False
    rep_completed: bool = False
    is_bad: bool = False
    reason: str = ""
    min_knee_angle: Optional[float] = None


class SquatRepCounter:
    """Track squat reps and basic form errors (e.g., too shallow)."""

    def __init__(self) -> None:
        self.rep_count = 0
        self.bad_rep_count = 0
        self.last_rep_result = "none"
        self._down_frames = 0
        self._in_rep = False
        self._rep_start_time = 0.0
        self._min_knee_angle: Optional[float] = None

    def update(self, squat_state: SquatState, timestamp: float) -> RepCounterUpdate:
        if squat_state.label == "no_pose":
            self._down_frames = 0
            return RepCounterUpdate()

        if squat_state.label == "down":
            self._down_frames += 1
            if squat_state.knee_angle is not None:
                if self._min_knee_angle is None:
                    self._min_knee_angle = squat_state.knee_angle
                else:
                    self._min_knee_angle = min(
                        self._min_knee_angle, squat_state.knee_angle
                    )

            if not self._in_rep and self._down_frames >= SQUAT_CONFIG.down_hold_frames:
                self._in_rep = True
                self._rep_start_time = timestamp
                return RepCounterUpdate(
                    rep_started=True,
                    min_knee_angle=self._min_knee_angle,
                )
        else:
            self._down_frames = 0

        if self._in_rep and squat_state.label == "standing":
            if timestamp - self._rep_start_time >= SQUAT_CONFIG.min_rep_seconds:
                min_angle = self._min_knee_angle
                is_bad = (
                    min_angle is None
                    or min_angle > SQUAT_CONFIG.shallow_knee_angle
                )
                reason = "too_shallow" if is_bad else ""

                self.rep_count += 1
                if is_bad:
                    self.bad_rep_count += 1

                self.last_rep_result = "too_shallow" if is_bad else "ok"

                self._in_rep = False
                self._min_knee_angle = None

                return RepCounterUpdate(
                    rep_completed=True,
                    is_bad=is_bad,
                    reason=reason,
                    min_knee_angle=min_angle,
                )

        return RepCounterUpdate()
