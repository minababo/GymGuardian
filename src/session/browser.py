"""Session browser helpers for loading and opening saved sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Optional

from session.insights import bad_rep_percentage, build_recommendation


@dataclass(frozen=True)
class SessionBrowserItem:
    """Represents one saved session folder and its metadata."""

    folder_name: str
    folder_path: Path
    video_path: Path
    summary_path: Path
    valid_session: bool
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
    latest_avg_fps: Optional[float] = None
    latest_most_common_issue: Optional[str] = None
    previous_timestamp: Optional[str] = None
    previous_rep_count: Optional[int] = None
    rep_count_change: Optional[int] = None
    bad_rep_percentage_change: Optional[float] = None
    avg_knee_angle_change: Optional[float] = None
    avg_fps_overall: Optional[float] = None
    trend_sessions: tuple["AnalyticsTrendItem", ...] = field(default_factory=tuple)
    issue_totals: dict[str, int] = field(default_factory=dict)
    main_concern: Optional[str] = None
    suggested_improvement: Optional[str] = None
    focus_area: Optional[str] = None


@dataclass(frozen=True)
class AnalyticsTrendItem:
    """Compact session row used for analytics trend display and export."""

    folder_name: str
    rep_count: int
    bad_rep_count: int
    bad_rep_percentage: Optional[float]
    avg_knee_angle: Optional[float]
    avg_ankle_angle: Optional[float]
    avg_torso_angle: Optional[float]
    avg_fps: Optional[float]
    most_common_issue: Optional[str]


@dataclass(frozen=True)
class AnalyticsSessionItem:
    """Saved session data used by the analytics dashboard."""

    folder_name: str
    valid_session: bool
    rep_count: int
    bad_rep_count: int
    avg_knee_angle: Optional[float]
    min_knee_angle: Optional[float]
    avg_ankle_angle: Optional[float]
    avg_torso_angle: Optional[float]
    avg_fps: Optional[float]
    issue_counts: dict[str, int]
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
        valid_session = _derive_valid_session(data, rep_count)

        items.append(
            SessionBrowserItem(
                folder_name=_format_session_label(folder.name, valid_session),
                folder_path=folder,
                video_path=video_path,
                summary_path=summary_path,
                valid_session=valid_session,
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

    latest_bad_rep_percentage = bad_rep_percentage(latest.rep_count, latest.bad_rep_count)
    previous_bad_rep_percentage = (
        bad_rep_percentage(previous.rep_count, previous.bad_rep_count)
        if previous
        else None
    )
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

    main_concern, suggested_improvement, focus_area = build_recommendation(
        latest.most_common_issue
    )
    trend_sessions = tuple(
        _build_trend_item(session) for session in meaningful_sessions[:15]
    )
    issue_totals = _aggregate_issue_counts(meaningful_sessions)
    avg_fps_overall = _average_optional(
        [session.avg_fps for session in meaningful_sessions]
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
        latest_avg_fps=latest.avg_fps,
        latest_most_common_issue=latest.most_common_issue,
        previous_timestamp=previous.folder_name if previous else None,
        previous_rep_count=previous.rep_count if previous else None,
        rep_count_change=rep_count_change,
        bad_rep_percentage_change=bad_rep_percentage_change,
        avg_knee_angle_change=avg_knee_angle_change,
        avg_fps_overall=avg_fps_overall,
        trend_sessions=trend_sessions,
        issue_totals=issue_totals,
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
                valid_session=_derive_valid_session(data, rep_count),
                rep_count=rep_count,
                bad_rep_count=bad_rep_count,
                avg_knee_angle=_safe_float(data.get("avg_knee_angle")),
                min_knee_angle=_safe_float(data.get("min_knee_angle")),
                avg_ankle_angle=_safe_float(data.get("avg_ankle_angle")),
                avg_torso_angle=_safe_float(data.get("avg_torso_angle")),
                avg_fps=_safe_float(data.get("avg_fps")),
                issue_counts=_safe_issue_counts(data.get("issue_counts")),
                most_common_issue=most_common_issue,
            )
        )

    return analytics_sessions


def _is_meaningful_session(session: AnalyticsSessionItem) -> bool:
    return session.valid_session and session.rep_count > 0


def _derive_valid_session(data: Optional[dict], rep_count: Optional[int]) -> bool:
    if not data:
        return False

    explicit_flag = _safe_bool(data.get("valid_session"))
    if explicit_flag is not None:
        return explicit_flag

    return rep_count is not None and rep_count > 0


def _format_session_label(folder_name: str, valid_session: bool) -> str:
    if valid_session:
        return folder_name
    return f"{folder_name} (incomplete)"


def _safe_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return None


def _safe_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_issue_counts(value) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}

    issue_counts: dict[str, int] = {}
    for issue, count in value.items():
        issue_name = str(issue).strip()
        if not issue_name:
            continue
        safe_count = _safe_int(count)
        if safe_count is None or safe_count <= 0:
            continue
        issue_counts[issue_name] = safe_count
    return issue_counts


def _aggregate_issue_counts(
    sessions: list[AnalyticsSessionItem],
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for session in sessions:
        for issue, count in session.issue_counts.items():
            totals[issue] = totals.get(issue, 0) + count

    return dict(
        sorted(
            totals.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )


def _build_trend_item(session: AnalyticsSessionItem) -> AnalyticsTrendItem:
    return AnalyticsTrendItem(
        folder_name=session.folder_name,
        rep_count=session.rep_count,
        bad_rep_count=session.bad_rep_count,
        bad_rep_percentage=bad_rep_percentage(session.rep_count, session.bad_rep_count),
        avg_knee_angle=session.avg_knee_angle,
        avg_ankle_angle=session.avg_ankle_angle,
        avg_torso_angle=session.avg_torso_angle,
        avg_fps=session.avg_fps,
        most_common_issue=session.most_common_issue,
    )


def _average_optional(values: list[Optional[float]]) -> Optional[float]:
    valid_values = [value for value in values if value is not None]
    if not valid_values:
        return None
    return round(sum(valid_values) / len(valid_values), 2)
