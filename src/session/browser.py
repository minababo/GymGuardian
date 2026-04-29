"""Session browser helpers for loading and opening saved sessions."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SessionBrowserItem:
    """Represents one saved session folder and its metadata."""

    folder_name: str
    folder_path: Path
    video_path: Path
    summary_path: Path
    rep_count: Optional[int]
    bad_rep_count: Optional[int]


@dataclass(frozen=True)
class AnalyticsSnapshot:
    """Aggregate analytics view used by the dashboard."""

    total_sessions: int = 0
    meaningful_session_count: int = 0
    latest_timestamp: Optional[str] = None
    latest_rep_count: Optional[int] = None
    latest_bad_rep_count: Optional[int] = None
    latest_bad_rep_percentage: Optional[float] = None
    latest_avg_knee_angle: Optional[float] = None
    latest_min_knee_angle: Optional[float] = None
    latest_avg_ankle_angle: Optional[float] = None
    latest_avg_torso_angle: Optional[float] = None
    latest_most_common_issue: Optional[str] = None
    previous_timestamp: Optional[str] = None
    previous_rep_count: Optional[int] = None
    rep_count_change: Optional[int] = None
    bad_rep_percentage_change: Optional[float] = None
    avg_knee_angle_change: Optional[float] = None
    main_concern: Optional[str] = None
    suggested_improvement: Optional[str] = None
    focus_area: Optional[str] = None


@dataclass(frozen=True)
class AnalyticsSessionItem:
    """Saved session data used by the analytics dashboard."""

    folder_name: str
    rep_count: int
    bad_rep_count: int
    avg_knee_angle: Optional[float]
    min_knee_angle: Optional[float]
    avg_ankle_angle: Optional[float]
    avg_torso_angle: Optional[float]
    most_common_issue: Optional[str]


def list_recent_sessions(
    sessions_dir: Path, limit: Optional[int] = 30
) -> list[SessionBrowserItem]:
    """Return saved sessions sorted newest-first by timestamp folder name."""
    if not sessions_dir.exists():
        return []

    folders = [path for path in sessions_dir.iterdir() if path.is_dir()]
    folders.sort(key=lambda path: path.name, reverse=True)
    if limit is not None:
        folders = folders[:limit]

    items: list[SessionBrowserItem] = []
    for folder in folders:
        summary_path = folder / "summary.json"
        video_path = folder / "session.mp4"
        data = _load_summary_data(summary_path)
        rep_count = _safe_int(data.get("rep_count")) if data else None
        bad_rep_count = _safe_int(data.get("bad_rep_count")) if data else None

        items.append(
            SessionBrowserItem(
                folder_name=folder.name,
                folder_path=folder,
                video_path=video_path,
                summary_path=summary_path,
                rep_count=rep_count,
                bad_rep_count=bad_rep_count,
            )
        )

    return items


def load_analytics_snapshot(sessions_dir: Path) -> AnalyticsSnapshot:
    """Load analytics from saved session summaries."""
    recent_sessions = list_recent_sessions(sessions_dir, limit=None)
    analytics_sessions = _load_analytics_sessions(recent_sessions)
    meaningful_sessions = [
        session for session in analytics_sessions if _is_meaningful_session(session)
    ]

    if not meaningful_sessions:
        return AnalyticsSnapshot(
            total_sessions=len(recent_sessions),
            meaningful_session_count=0,
        )

    latest = meaningful_sessions[0]
    previous = meaningful_sessions[1] if len(meaningful_sessions) > 1 else None

    latest_bad_rep_percentage = _bad_rep_percentage(latest)
    previous_bad_rep_percentage = _bad_rep_percentage(previous) if previous else None
    rep_count_change = None
    bad_rep_percentage_change = None
    avg_knee_angle_change = None

    if previous is not None:
        rep_count_change = latest.rep_count - previous.rep_count
        if (
            latest_bad_rep_percentage is not None
            and previous_bad_rep_percentage is not None
        ):
            bad_rep_percentage_change = round(
                latest_bad_rep_percentage - previous_bad_rep_percentage,
                2,
            )
        if latest.avg_knee_angle is not None and previous.avg_knee_angle is not None:
            avg_knee_angle_change = round(
                latest.avg_knee_angle - previous.avg_knee_angle,
                2,
            )

    main_concern, suggested_improvement, focus_area = _build_recommendation(
        latest.most_common_issue
    )

    return AnalyticsSnapshot(
        total_sessions=len(recent_sessions),
        meaningful_session_count=len(meaningful_sessions),
        latest_timestamp=latest.folder_name,
        latest_rep_count=latest.rep_count,
        latest_bad_rep_count=latest.bad_rep_count,
        latest_bad_rep_percentage=latest_bad_rep_percentage,
        latest_avg_knee_angle=latest.avg_knee_angle,
        latest_min_knee_angle=latest.min_knee_angle,
        latest_avg_ankle_angle=latest.avg_ankle_angle,
        latest_avg_torso_angle=latest.avg_torso_angle,
        latest_most_common_issue=latest.most_common_issue,
        previous_timestamp=previous.folder_name if previous else None,
        previous_rep_count=previous.rep_count if previous else None,
        rep_count_change=rep_count_change,
        bad_rep_percentage_change=bad_rep_percentage_change,
        avg_knee_angle_change=avg_knee_angle_change,
        main_concern=main_concern,
        suggested_improvement=suggested_improvement,
        focus_area=focus_area,
    )


def open_session_video(session: SessionBrowserItem) -> None:
    """Open a session video in the default media player on Windows."""
    if not session.video_path.exists():
        print(f"Warning: session video not found at {session.video_path}")
        return

    os.startfile(str(session.video_path))


def open_session_folder(session: SessionBrowserItem) -> None:
    """Open the session folder in Windows Explorer."""
    if not session.folder_path.exists():
        print(f"Warning: session folder not found at {session.folder_path}")
        return

    os.startfile(str(session.folder_path))


def _load_summary_data(summary_path: Path) -> Optional[dict]:
    if not summary_path.exists():
        return None

    try:
        with summary_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return None


def _load_analytics_sessions(
    sessions: list[SessionBrowserItem],
) -> list[AnalyticsSessionItem]:
    analytics_sessions: list[AnalyticsSessionItem] = []

    for session in sessions:
        data = _load_summary_data(session.summary_path)
        if not data:
            continue

        rep_count = _safe_int(data.get("rep_count"))
        bad_rep_count = _safe_int(data.get("bad_rep_count"))
        if rep_count is None or bad_rep_count is None:
            continue

        most_common_issue = data.get("most_common_issue")
        if most_common_issue is not None:
            most_common_issue = str(most_common_issue)

        analytics_sessions.append(
            AnalyticsSessionItem(
                folder_name=session.folder_name,
                rep_count=rep_count,
                bad_rep_count=bad_rep_count,
                avg_knee_angle=_safe_float(data.get("avg_knee_angle")),
                min_knee_angle=_safe_float(data.get("min_knee_angle")),
                avg_ankle_angle=_safe_float(data.get("avg_ankle_angle")),
                avg_torso_angle=_safe_float(data.get("avg_torso_angle")),
                most_common_issue=most_common_issue,
            )
        )

    return analytics_sessions


def _is_meaningful_session(session: AnalyticsSessionItem) -> bool:
    return session.rep_count > 0


def _bad_rep_percentage(session: AnalyticsSessionItem | None) -> Optional[float]:
    if session is None:
        return None
    if session.rep_count <= 0:
        return 0.0
    return round((session.bad_rep_count / session.rep_count) * 100.0, 2)


def _build_recommendation(
    issue: Optional[str],
) -> tuple[str, str, str]:
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
            "Improve ankle stability and foot positioning.",
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


def _issue_matches(issue: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in issue for keyword in keywords)


def _safe_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
