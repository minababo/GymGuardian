"""Automated tests for squat angle and repetition logic."""

from __future__ import annotations

import math

import pytest

from analysis.squat import SquatRepCounter, SquatState, SquatStateAnalyzer, _angle_degrees
from core.config import SQUAT_CONFIG, SquatConfig


def _state(
    knee: float,
    ankle: float = 70.0,
    torso: float = 8.0,
    quality_knee: float | None = None,
) -> SquatState:
    if knee >= 160:
        label = "standing"
    elif knee <= 100:
        label = "down"
    else:
        label = "transition"
    return SquatState(
        label=label,
        knee_angle=knee,
        ankle_angle=ankle,
        torso_angle=torso,
        pose_visible=True,
        quality_knee_angle=quality_knee,
    )


def _test_config() -> SquatConfig:
    return SquatConfig(
        down_knee_angle=100.0,
        up_knee_angle=160.0,
        rep_bottom_knee_angle=140.0,
        shallow_knee_angle=110.0,
        ankle_control_angle=88.0,
        torso_lean_angle=34.0,
        down_hold_frames=2,
        ready_standing_frames=2,
        no_pose_reset_frames=2,
        min_rep_seconds=0.2,
    )


class _Landmark:
    def __init__(self, x: float, y: float, visibility: float = 1.0) -> None:
        self.x = x
        self.y = y
        self.visibility = visibility
        self.presence = visibility


class _PoseResult:
    def __init__(self, landmarks) -> None:
        self.pose_landmarks = [landmarks]


def _blank_landmarks() -> list[_Landmark]:
    return [_Landmark(0.0, 0.0, 0.0) for _ in range(33)]


def _set_leg(
    landmarks: list[_Landmark],
    hip_i: int,
    knee_i: int,
    ankle_i: int,
    angle: float,
    visibility: float = 0.9,
) -> None:
    radians = math.radians(angle)
    landmarks[hip_i] = _Landmark(1.0, 0.0, visibility)
    landmarks[knee_i] = _Landmark(0.0, 0.0, visibility)
    landmarks[ankle_i] = _Landmark(math.cos(radians), math.sin(radians), visibility)


def test_angle_degrees_returns_angle_at_middle_point() -> None:
    assert _angle_degrees((1, 0), (0, 0), (0, 1)) == pytest.approx(90.0)
    assert _angle_degrees((1, 0), (0, 0), (1, 0)) == pytest.approx(0.0)


def test_analyzer_uses_visible_side_instead_of_returning_no_pose() -> None:
    landmarks = _blank_landmarks()
    landmarks[24] = _Landmark(0.0, 0.0, 0.9)
    landmarks[26] = _Landmark(0.0, 1.0, 0.9)
    landmarks[28] = _Landmark(1.0, 1.0, 0.9)
    landmarks[12] = _Landmark(0.0, -0.5, 0.9)

    analyzer = SquatStateAnalyzer(_test_config())
    state = analyzer.classify(_PoseResult(landmarks))

    assert state.pose_visible is True
    assert state.label == "down"
    assert state.knee_angle == pytest.approx(90.0)


def test_analyzer_keeps_conservative_quality_angle_for_back_view_noise() -> None:
    landmarks = _blank_landmarks()
    _set_leg(landmarks, 23, 25, 27, 90.0)
    _set_leg(landmarks, 24, 26, 28, 130.0)

    analyzer = SquatStateAnalyzer(_test_config())
    state = analyzer.classify(_PoseResult(landmarks))

    assert state.knee_angle == pytest.approx(90.0)
    assert state.quality_knee_angle == pytest.approx(130.0)


def test_rep_counter_counts_full_depth_rep_as_good() -> None:
    counter = SquatRepCounter(_test_config())

    updates = [
        counter.update(_state(170), 0.0),
        counter.update(_state(170), 0.1),
        counter.update(_state(130), 0.2),
        counter.update(_state(95), 0.3),
        counter.update(_state(90), 0.4),
        counter.update(_state(170), 0.7),
    ]

    assert any(update.rep_started for update in updates)
    complete = updates[-1]
    assert complete.rep_completed is True
    assert complete.is_bad is False
    assert complete.issues == ()
    assert counter.rep_count == 1
    assert counter.bad_rep_count == 0
    assert counter.last_rep_result == "ok"


def test_rep_counter_flags_shallow_rep_as_bad() -> None:
    counter = SquatRepCounter(_test_config())

    for timestamp, knee in [
        (0.0, 170),
        (0.1, 170),
        (0.2, 132),
        (0.3, 130),
        (0.4, 128),
    ]:
        counter.update(_state(knee), timestamp)
    complete = counter.update(_state(170), 0.7)

    assert complete.rep_completed is True
    assert complete.is_bad is True
    assert "too_shallow" in complete.issues
    assert counter.rep_count == 1
    assert counter.bad_rep_count == 1


def test_quality_knee_angle_flags_noisy_back_view_shallow_rep() -> None:
    counter = SquatRepCounter(_test_config())

    for timestamp, knee, quality in [
        (0.0, 170, 170),
        (0.1, 170, 170),
        (0.2, 150, 150),
        (0.3, 90, 130),
        (0.4, 90, 130),
        (0.5, 90, 130),
    ]:
        counter.update(_state(knee, quality_knee=quality), timestamp)
    complete = counter.update(_state(170, quality_knee=170), 0.8)

    assert complete.rep_completed is True
    assert complete.is_bad is True
    assert "too_shallow" in complete.issues
    assert counter.rep_count == 1
    assert counter.bad_rep_count == 1


def test_default_ankle_threshold_does_not_warn_on_normal_ankle_angle() -> None:
    counter = SquatRepCounter(SQUAT_CONFIG)

    complete = None
    timestamp = 0.0
    for knee in [170, 170, 160, 150, 90, 90, 90, 90, 150, 160, 170, 170]:
        update = counter.update(_state(knee, ankle=165.0), timestamp)
        if update.rep_completed:
            complete = update
        timestamp += 0.1

    assert complete is not None
    assert "ankle_control" not in complete.issues


def test_default_thresholds_count_full_and_shallow_validation_sets() -> None:
    def run_reps(depths: list[float]) -> tuple[int, int]:
        counter = SquatRepCounter(SQUAT_CONFIG)
        timestamp = 0.0
        for depth in depths:
            for knee in [170, 170, 160, 150, depth, depth, depth, depth, 150, 160, 170, 170]:
                counter.update(_state(knee), timestamp)
                timestamp += 0.08
        return counter.rep_count, counter.bad_rep_count

    assert run_reps([90.0] * 10) == (10, 0)
    assert run_reps([130.0] * 5) == (5, 5)
    assert run_reps(([90.0] * 5) + ([130.0] * 5)) == (10, 5)


def test_no_pose_resets_incomplete_cycle_before_counting() -> None:
    counter = SquatRepCounter(_test_config())
    no_pose = SquatState(label="no_pose", knee_angle=None, pose_visible=False)

    counter.update(_state(170), 0.0)
    counter.update(_state(170), 0.1)
    counter.update(_state(130), 0.2)
    counter.update(no_pose, 0.3)
    counter.update(no_pose, 0.4)
    complete = counter.update(_state(170), 0.8)

    assert complete.rep_completed is False
    assert counter.rep_count == 0
    assert counter.bad_rep_count == 0
