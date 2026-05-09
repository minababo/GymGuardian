"""Shared rule-based insights for squat-session analytics."""

from __future__ import annotations

from typing import Optional


def build_recommendation(issue: Optional[str]) -> tuple[str, str, str]:
    normalized_issue = issue or ""
    if normalized_issue == "too_shallow":
        return (
            "Depth is the main concern.",
            "Increase squat depth and aim for a lower knee angle.",
            "Knee bend depth",
        )
    if _issue_matches(normalized_issue, ("ankle", "foot", "stability")):
        return (
            "Ankle control is the main concern.",
            "Keep feet planted and let knees track over toes without heel lift.",
            "Ankle control",
        )
    if _issue_matches(normalized_issue, ("torso", "back", "lean", "posture")):
        return (
            "Torso posture is the main concern.",
            "Keep torso more controlled and avoid excessive forward lean.",
            "Torso posture",
        )
    if normalized_issue:
        readable_issue = normalized_issue.replace("_", " ")
        return (
            f"Main concern: {readable_issue}.",
            "Maintain current form consistency.",
            "Consistency",
        )
    return (
        "No major form issue detected.",
        "Maintain current form consistency.",
        "Consistency",
    )


def bad_rep_percentage(rep_count: int, bad_rep_count: int) -> float:
    if rep_count <= 0:
        return 0.0
    return round((bad_rep_count / rep_count) * 100.0, 2)


def _issue_matches(issue: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in issue for keyword in keywords)
