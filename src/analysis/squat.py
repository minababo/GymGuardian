"""Squat state classification and rep counting for the squat coach prototype."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Deque, Optional

from core.config import SQUAT_CONFIG, SquatConfig


@dataclass(frozen=True)
class SquatState:
    label: str
    knee_angle: Optional[float]
    ankle_angle: Optional[float] = None
    torso_angle: Optional[float] = None
    pose_visible: bool = False
    quality_knee_angle: Optional[float] = None


@dataclass(frozen=True)
class _AngleCandidate:
    side: str
    angle: float
    confidence: float


class SquatStateAnalyzer:
    """Classify squat state from pose landmarks with light smoothing."""

    def __init__(self, config: SquatConfig | None = None) -> None:
        self._config = config or SQUAT_CONFIG
        window = max(1, self._config.angle_smoothing_window)
        self._knee_history: Deque[float] = deque(maxlen=window)
        self._quality_knee_history: Deque[float] = deque(maxlen=window)
        self._ankle_history: Deque[float] = deque(maxlen=window)
        self._torso_history: Deque[float] = deque(maxlen=window)
        self._missing_pose_frames = 0
        self._active_side: Optional[str] = None

    def classify(self, pose_result) -> SquatState:
        # pose_result.pose_landmarks -> list of poses; each pose -> list of landmarks
        if pose_result is None or not getattr(pose_result, "pose_landmarks", None):
            self._mark_missing_pose()
            return SquatState(label="no_pose", knee_angle=None)
        if len(pose_result.pose_landmarks) == 0:
            self._mark_missing_pose()
            return SquatState(label="no_pose", knee_angle=None)

        landmarks = pose_result.pose_landmarks[0]

        left_knee = self._angle_candidate_if_visible(landmarks, "left", 23, 25, 27)
        right_knee = self._angle_candidate_if_visible(landmarks, "right", 24, 26, 28)
        knee_candidate = self._select_angle_candidate(
            left_knee,
            right_knee,
            prefer_lower=True,
        )
        if knee_candidate is None:
            # Treat missing lower-body landmarks on both sides as no pose for rep logic.
            self._mark_missing_pose()
            return SquatState(label="no_pose", knee_angle=None)

        self._sync_active_side(knee_candidate.side)
        knee_angle = self._smooth_metric(self._knee_history, knee_candidate.angle)
        quality_knee_angle = self._smooth_metric(
            self._quality_knee_history,
            self._quality_knee_angle(knee_candidate, left_knee, right_knee),
        )

        ankle_candidate = self._side_candidate_or_best(
            landmarks,
            knee_candidate.side,
            ("left", 25, 27, 31),
            ("right", 26, 28, 32),
            prefer_lower=False,
        )
        torso_candidate = self._torso_side_candidate_or_best(
            landmarks,
            knee_candidate.side,
        )
        ankle_angle = (
            self._smooth_metric(self._ankle_history, ankle_candidate.angle)
            if ankle_candidate is not None
            else None
        )
        torso_angle = (
            self._smooth_metric(self._torso_history, torso_candidate.angle)
            if torso_candidate is not None
            else None
        )

        self._missing_pose_frames = 0
        if knee_angle <= self._config.down_knee_angle:
            label = "down"
        elif knee_angle >= self._config.up_knee_angle:
            label = "standing"
        else:
            label = "transition"

        return SquatState(
            label=label,
            knee_angle=knee_angle,
            ankle_angle=ankle_angle,
            torso_angle=torso_angle,
            pose_visible=True,
            quality_knee_angle=quality_knee_angle,
        )

    def _angle_candidate_if_visible(
        self, landmarks, side: str, point_a: int, point_b: int, point_c: int
    ) -> Optional[_AngleCandidate]:
        if not self._landmarks_visible(landmarks, point_a, point_b, point_c):
            return None

        landmark_a = landmarks[point_a]
        landmark_b = landmarks[point_b]
        landmark_c = landmarks[point_c]
        angle = _angle_degrees(
            (landmark_a.x, landmark_a.y),
            (landmark_b.x, landmark_b.y),
            (landmark_c.x, landmark_c.y),
        )
        confidence = min(
            self._landmark_confidence(landmark_a),
            self._landmark_confidence(landmark_b),
            self._landmark_confidence(landmark_c),
        )
        return _AngleCandidate(side=side, angle=angle, confidence=confidence)

    def _select_angle_candidate(
        self,
        first: Optional[_AngleCandidate],
        second: Optional[_AngleCandidate],
        *,
        prefer_lower: bool,
    ) -> Optional[_AngleCandidate]:
        candidates = [candidate for candidate in (first, second) if candidate is not None]
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        left, right = candidates
        if abs(left.confidence - right.confidence) >= 0.15:
            return max(candidates, key=lambda candidate: candidate.confidence)
        if prefer_lower:
            return min(candidates, key=lambda candidate: candidate.angle)
        return max(candidates, key=lambda candidate: candidate.confidence)

    def _quality_knee_angle(
        self,
        selected: _AngleCandidate,
        first: Optional[_AngleCandidate],
        second: Optional[_AngleCandidate],
    ) -> float:
        candidates = [candidate for candidate in (first, second) if candidate is not None]
        if len(candidates) <= 1:
            return selected.angle

        best_confidence = max(candidate.confidence for candidate in candidates)
        reliable = [
            candidate
            for candidate in candidates
            if best_confidence - candidate.confidence <= 0.12
        ]
        if not reliable:
            return selected.angle
        # Quality checks are conservative: one noisy-looking deep side should not
        # hide a shallow rep when the other side remains reliably visible.
        return max(candidate.angle for candidate in reliable)

    def _side_candidate_or_best(
        self,
        landmarks,
        preferred_side: str,
        left_points: tuple[str, int, int, int],
        right_points: tuple[str, int, int, int],
        *,
        prefer_lower: bool,
    ) -> Optional[_AngleCandidate]:
        left = self._angle_candidate_if_visible(landmarks, *left_points)
        right = self._angle_candidate_if_visible(landmarks, *right_points)
        preferred = left if preferred_side == "left" else right
        if preferred is not None:
            return preferred
        return self._select_angle_candidate(left, right, prefer_lower=prefer_lower)

    def _torso_side_candidate_or_best(
        self, landmarks, preferred_side: str
    ) -> Optional[_AngleCandidate]:
        left = self._torso_candidate_if_visible(landmarks, "left", 11, 23)
        right = self._torso_candidate_if_visible(landmarks, "right", 12, 24)
        preferred = left if preferred_side == "left" else right
        if preferred is not None:
            return preferred
        return self._select_angle_candidate(left, right, prefer_lower=False)

    def _angle_if_visible(
        self, landmarks, point_a: int, point_b: int, point_c: int
    ) -> Optional[float]:
        candidate = self._angle_candidate_if_visible(
            landmarks, "unknown", point_a, point_b, point_c
        )
        return candidate.angle if candidate is not None else None

    def _torso_angle_if_visible(
        self, landmarks, shoulder_i: int, hip_i: int
    ) -> Optional[float]:
        candidate = self._torso_candidate_if_visible(
            landmarks, "unknown", shoulder_i, hip_i
        )
        return candidate.angle if candidate is not None else None

    def _torso_candidate_if_visible(
        self, landmarks, side: str, shoulder_i: int, hip_i: int
    ) -> Optional[_AngleCandidate]:
        if not self._landmarks_visible(landmarks, shoulder_i, hip_i):
            return None

        shoulder = landmarks[shoulder_i]
        hip = landmarks[hip_i]
        dx = shoulder.x - hip.x
        dy = shoulder.y - hip.y

        vertical_span = abs(dy)
        if dx == 0 and dy == 0:
            angle = 0.0
        elif vertical_span == 0:
            angle = 90.0
        else:
            angle = math.degrees(math.atan2(abs(dx), vertical_span))

        confidence = min(
            self._landmark_confidence(shoulder),
            self._landmark_confidence(hip),
        )
        return _AngleCandidate(side=side, angle=angle, confidence=confidence)

    def _maybe_smooth_angle(
        self,
        history: Deque[float],
        first_value: Optional[float],
        second_value: Optional[float],
    ) -> Optional[float]:
        values = [value for value in (first_value, second_value) if value is not None]
        if not values:
            return None
        return self._smooth_metric(history, sum(values) / len(values))

    def _smooth_metric(self, history: Deque[float], value: float) -> float:
        history.append(value)
        return sum(history) / len(history)

    def _sync_active_side(self, side: str) -> None:
        if self._active_side is not None and self._active_side != side:
            self._knee_history.clear()
            self._quality_knee_history.clear()
            self._ankle_history.clear()
            self._torso_history.clear()
        self._active_side = side

    def _mark_missing_pose(self) -> None:
        self._missing_pose_frames += 1
        if self._missing_pose_frames >= self._config.no_pose_reset_frames:
            self._knee_history.clear()
            self._quality_knee_history.clear()
            self._ankle_history.clear()
            self._torso_history.clear()
            self._active_side = None

    def _landmarks_visible(self, landmarks, *indices: int) -> bool:
        if not landmarks or max(indices) >= len(landmarks):
            return False
        confidences = [self._landmark_confidence(landmarks[index]) for index in indices]
        coords_ok = all(
            math.isfinite(getattr(landmarks[index], "x", float("nan")))
            and math.isfinite(getattr(landmarks[index], "y", float("nan")))
            for index in indices
        )
        return coords_ok and min(confidences) >= self._config.landmark_visibility_threshold

    @staticmethod
    def _landmark_confidence(landmark) -> float:
        visibility = getattr(landmark, "visibility", 1.0)
        presence = getattr(landmark, "presence", visibility)
        try:
            return min(float(visibility), float(presence))
        except (TypeError, ValueError):
            return 0.0



def _angle_degrees(a, b, c) -> float:
    """Return the angle at point b (in degrees) for triangle a-b-c."""
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
    issues: tuple[str, ...] = ()
    min_knee_angle: Optional[float] = None
    min_ankle_angle: Optional[float] = None
    max_torso_angle: Optional[float] = None


class SquatRepCounter:
    """Track squat reps while keeping quality checks rule-based and separate."""

    def __init__(self, config: SquatConfig | None = None) -> None:
        self._config = config or SQUAT_CONFIG
        self.rep_count = 0
        self.bad_rep_count = 0
        self.last_rep_result = "none"
        self._bottom_frames = 0
        self._standing_frames = 0
        self._missing_pose_frames = 0
        self._in_rep = False
        self._ready_for_rep = False
        self._rep_start_time: Optional[float] = None
        self._min_knee_angle: Optional[float] = None
        self._min_ankle_angle: Optional[float] = None
        self._max_torso_angle: Optional[float] = None

    def update(self, squat_state: SquatState, timestamp: float) -> RepCounterUpdate:
        if squat_state.label == "no_pose" or not squat_state.pose_visible:
            return self._handle_missing_pose()

        angle = squat_state.knee_angle
        if angle is None:
            return self._handle_missing_pose()

        self._missing_pose_frames = 0

        if angle >= self._config.up_knee_angle:
            self._standing_frames += 1
            if not self._in_rep and self._standing_frames >= self._config.ready_standing_frames:
                self._ready_for_rep = True
                self._bottom_frames = 0
                self._rep_start_time = None
                self._clear_cycle_metrics()
        else:
            self._standing_frames = 0

        if self._in_rep:
            self._update_cycle_metrics(squat_state)
            if (
                self._rep_start_time is not None
                and timestamp - self._rep_start_time >= self._config.min_rep_seconds
                and angle >= self._config.up_knee_angle
            ):
                return self._complete_rep()
            return RepCounterUpdate()

        if not self._ready_for_rep:
            return RepCounterUpdate()

        if angle < self._config.up_knee_angle:
            if self._rep_start_time is None:
                self._rep_start_time = timestamp
            self._update_cycle_metrics(squat_state)

        if angle <= self._config.rep_bottom_knee_angle:
            self._bottom_frames += 1
            if self._bottom_frames >= self._config.down_hold_frames:
                self._in_rep = True
                if self._rep_start_time is None:
                    self._rep_start_time = timestamp
                return RepCounterUpdate(
                    rep_started=True,
                    min_knee_angle=self._min_knee_angle,
                    min_ankle_angle=self._min_ankle_angle,
                    max_torso_angle=self._max_torso_angle,
                )
        elif angle >= self._config.down_knee_angle:
            self._bottom_frames = 0

        return RepCounterUpdate()

    def _handle_missing_pose(self) -> RepCounterUpdate:
        self._bottom_frames = 0
        self._standing_frames = 0
        self._missing_pose_frames += 1
        if self._missing_pose_frames >= self._config.no_pose_reset_frames:
            self._reset_cycle_state()
        return RepCounterUpdate()

    def _update_cycle_metrics(self, squat_state: SquatState) -> None:
        knee_angle = (
            squat_state.quality_knee_angle
            if squat_state.quality_knee_angle is not None
            else squat_state.knee_angle
        )
        if knee_angle is not None:
            if self._min_knee_angle is None:
                self._min_knee_angle = knee_angle
            else:
                self._min_knee_angle = min(self._min_knee_angle, knee_angle)

        ankle_angle = squat_state.ankle_angle
        if ankle_angle is not None:
            if self._min_ankle_angle is None:
                self._min_ankle_angle = ankle_angle
            else:
                self._min_ankle_angle = min(self._min_ankle_angle, ankle_angle)

        torso_angle = squat_state.torso_angle
        if torso_angle is not None:
            if self._max_torso_angle is None:
                self._max_torso_angle = torso_angle
            else:
                self._max_torso_angle = max(self._max_torso_angle, torso_angle)

    def _complete_rep(self) -> RepCounterUpdate:
        min_knee_angle = self._min_knee_angle
        min_ankle_angle = self._min_ankle_angle
        max_torso_angle = self._max_torso_angle

        issues: list[str] = []
        if min_knee_angle is None or min_knee_angle > self._config.shallow_knee_angle:
            issues.append("too_shallow")
        if (
            min_ankle_angle is not None
            and min_ankle_angle > self._config.ankle_control_angle
        ):
            issues.append("ankle_control")
        if (
            max_torso_angle is not None
            and max_torso_angle > self._config.torso_lean_angle
        ):
            issues.append("torso_lean")

        is_bad = "too_shallow" in issues
        reason = ", ".join(issues)

        self.rep_count += 1
        if is_bad:
            self.bad_rep_count += 1

        self.last_rep_result = reason if reason else "ok"
        self._reset_cycle_state(keep_ready=True)

        return RepCounterUpdate(
            rep_completed=True,
            is_bad=is_bad,
            reason=reason,
            issues=tuple(issues),
            min_knee_angle=min_knee_angle,
            min_ankle_angle=min_ankle_angle,
            max_torso_angle=max_torso_angle,
        )

    def _clear_cycle_metrics(self) -> None:
        self._min_knee_angle = None
        self._min_ankle_angle = None
        self._max_torso_angle = None

    def _reset_cycle_state(self, keep_ready: bool = False) -> None:
        self._bottom_frames = 0
        self._standing_frames = 0
        self._in_rep = False
        self._ready_for_rep = keep_ready
        self._rep_start_time = None
        self._clear_cycle_metrics()
