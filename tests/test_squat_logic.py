"""Automated tests for squat angle and repetition logic."""

from __future__ import annotations

import pytest

from analysis.squat import SquatRepCounter, SquatState, _angle_degrees
from core.config import SquatConfig


def _state(knee: float, ankle: float = 70.0, torso: float = 8.0) -> SquatState:
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


def test_angle_degrees_returns_angle_at_middle_point() -> None:
    assert _angle_degrees((1, 0), (0, 0), (0, 1)) == pytest.approx(90.0)
    assert _angle_degrees((1, 0), (0, 0), (1, 0)) == pytest.approx(0.0)


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
