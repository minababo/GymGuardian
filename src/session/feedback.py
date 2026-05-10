"""Shared live-feedback wording for rep results and in-progress cues."""

from __future__ import annotations

from core.config import SquatConfig


def current_feedback(
    squat_state,
    feedback_message: str | None,
    feedback_level: str,
    feedback_until: float,
    timestamp: float,
    squat_config: SquatConfig,
    *,
    is_in_rep: bool = False,
) -> tuple[str | None, str]:
    if feedback_message and timestamp <= feedback_until:
        return feedback_message, feedback_level

    angle = squat_state.knee_angle
    if (
        not is_in_rep
        and angle is not None
        and squat_config.shallow_knee_angle < angle <= squat_config.rep_bottom_knee_angle
    ):
        return "Go deeper", "warning"

    return None, "info"


def rep_feedback(issues: tuple[str, ...], is_bad: bool) -> tuple[str, str]:
    if is_bad and "too_shallow" in issues:
        return "Bad rep: lower hips and bend knees more", "bad"
    if "torso_lean" in issues and "ankle_control" in issues:
        return "Rep logged: feet flat, knees over toes, chest up", "warning"
    if "torso_lean" in issues:
        return "Rep logged: brace core and keep chest up", "warning"
    if "ankle_control" in issues:
        return "Rep logged: keep feet flat; knees track over toes", "warning"
    return "Rep accepted", "ok"
