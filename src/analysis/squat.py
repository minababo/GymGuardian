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
    ankle_angle: Optional[float] = None
    torso_angle: Optional[float] = None


class SquatStateAnalyzer:
    """Classify a squat and expose simple joint-angle analytics."""

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
        knee_angle = self._average_angle(
            [
                self._angle_if_visible(landmarks, 23, 25, 27),
                self._angle_if_visible(landmarks, 24, 26, 28),
            ]
        )
        ankle_angle = self._average_angle(
            [
                self._angle_if_visible(landmarks, 25, 27, 31),
                self._angle_if_visible(landmarks, 26, 28, 32),
            ]
        )
        torso_angle = self._average_angle(
            [
                self._torso_angle_if_visible(landmarks, 11, 23),
                self._torso_angle_if_visible(landmarks, 12, 24),
            ]
        )

        if knee_angle is None:
            return SquatState(
                label="no_pose",
                knee_angle=None,
                ankle_angle=ankle_angle,
                torso_angle=torso_angle,
            )

        if knee_angle <= SQUAT_CONFIG.down_knee_angle:
            label = "down"
        elif knee_angle >= SQUAT_CONFIG.up_knee_angle:
            label = "standing"
        else:
            label = "transition"

        return SquatState(
            label=label,
            knee_angle=knee_angle,
            ankle_angle=ankle_angle,
            torso_angle=torso_angle,
        )

    def _angle_if_visible(
        self, landmarks, point_a: int, point_b: int, point_c: int
    ) -> Optional[float]:
        if not self._landmarks_visible(landmarks, point_a, point_b, point_c):
            return None

        landmark_a = landmarks[point_a]
        landmark_b = landmarks[point_b]
        landmark_c = landmarks[point_c]
        return _angle_degrees(
            (landmark_a.x, landmark_a.y),
            (landmark_b.x, landmark_b.y),
            (landmark_c.x, landmark_c.y),
        )

    def _torso_angle_if_visible(
        self, landmarks, shoulder_i: int, hip_i: int
    ) -> Optional[float]:
        if not self._landmarks_visible(landmarks, shoulder_i, hip_i):
            return None

        shoulder = landmarks[shoulder_i]
        hip = landmarks[hip_i]
        dx = shoulder.x - hip.x
        dy = shoulder.y - hip.y
        if dx == 0 and dy == 0:
            return 0.0

        vertical_span = abs(dy)
        if vertical_span == 0:
            return 90.0

        return math.degrees(math.atan2(abs(dx), vertical_span))

    @staticmethod
    def _landmarks_visible(landmarks, *indices: int) -> bool:
        visibilities = [getattr(landmarks[index], "visibility", 1.0) for index in indices]
        return min(visibilities) >= 0.5

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
    """Track squat reps separately from depth quality checks."""

    def __init__(self) -> None:
        self.rep_count = 0
        self.bad_rep_count = 0
        self.last_rep_result = "none"
        self._bottom_frames = 0
        self._in_rep = False
        self._ready_for_rep = False
        self._rep_start_time = 0.0
        self._min_knee_angle: Optional[float] = None

    def update(self, squat_state: SquatState, timestamp: float) -> RepCounterUpdate:
        if squat_state.label == "no_pose":
            self._bottom_frames = 0
            return RepCounterUpdate()

        angle = squat_state.knee_angle
        if angle is None:
            self._bottom_frames = 0
            return RepCounterUpdate()

        if self._in_rep:
            self._update_min_knee_angle(angle)
            if timestamp - self._rep_start_time >= SQUAT_CONFIG.min_rep_seconds:
                if angle >= SQUAT_CONFIG.up_knee_angle:
                    return self._complete_rep()

            return RepCounterUpdate()

        if angle >= SQUAT_CONFIG.up_knee_angle:
            self._ready_for_rep = True
            self._bottom_frames = 0
            self._min_knee_angle = None
            return RepCounterUpdate()

        if not self._ready_for_rep:
            return RepCounterUpdate()

        if angle <= SQUAT_CONFIG.rep_bottom_knee_angle:
            self._bottom_frames += 1
            self._update_min_knee_angle(angle)
            if self._bottom_frames >= SQUAT_CONFIG.down_hold_frames:
                self._in_rep = True
                self._rep_start_time = timestamp
                return RepCounterUpdate(
                    rep_started=True,
                    min_knee_angle=self._min_knee_angle,
                )
        else:
            self._bottom_frames = 0

        return RepCounterUpdate()

    def _update_min_knee_angle(self, angle: float) -> None:
        if self._min_knee_angle is None:
            self._min_knee_angle = angle
        else:
            self._min_knee_angle = min(self._min_knee_angle, angle)

    def _complete_rep(self) -> RepCounterUpdate:
        min_angle = self._min_knee_angle
        is_bad = min_angle is None or min_angle > SQUAT_CONFIG.shallow_knee_angle
        reason = "too_shallow" if is_bad else ""

        self.rep_count += 1
        if is_bad:
            self.bad_rep_count += 1

        self.last_rep_result = "too_shallow" if is_bad else "ok"
        self._bottom_frames = 0
        self._in_rep = False
        self._ready_for_rep = True
        self._rep_start_time = 0.0
        self._min_knee_angle = None

        return RepCounterUpdate(
            rep_completed=True,
            is_bad=is_bad,
            reason=reason,
            min_knee_angle=min_angle,
        )
