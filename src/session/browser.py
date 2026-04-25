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
    """Minimal aggregate view for the analytics dashboard."""

    total_sessions: int = 0
    latest_timestamp: Optional[str] = None
    latest_rep_count: Optional[int] = None
    latest_bad_rep_count: Optional[int] = None
    latest_bad_rep_percentage: Optional[float] = None
    previous_rep_count: Optional[int] = None
    rep_count_change: Optional[int] = None
    bad_rep_count_change: Optional[int] = None


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
    """Load lightweight aggregate analytics from saved session summaries."""
    sessions = list_recent_sessions(sessions_dir, limit=None)
    if not sessions:
        return AnalyticsSnapshot()

    latest = sessions[0]
    previous = sessions[1] if len(sessions) > 1 else None

    latest_rep_count = latest.rep_count
    latest_bad_rep_count = latest.bad_rep_count
    latest_bad_rep_percentage = None
    if latest_rep_count is not None and latest_bad_rep_count is not None:
        if latest_rep_count > 0:
            latest_bad_rep_percentage = (latest_bad_rep_count / latest_rep_count) * 100.0
        else:
            latest_bad_rep_percentage = 0.0

    previous_rep_count = previous.rep_count if previous else None
    rep_count_change = None
    bad_rep_count_change = None
    if previous and latest_rep_count is not None and previous.rep_count is not None:
        rep_count_change = latest_rep_count - previous.rep_count
    if previous and latest_bad_rep_count is not None and previous.bad_rep_count is not None:
        bad_rep_count_change = latest_bad_rep_count - previous.bad_rep_count

    return AnalyticsSnapshot(
        total_sessions=len(sessions),
        latest_timestamp=latest.folder_name,
        latest_rep_count=latest_rep_count,
        latest_bad_rep_count=latest_bad_rep_count,
        latest_bad_rep_percentage=latest_bad_rep_percentage,
        previous_rep_count=previous_rep_count,
        rep_count_change=rep_count_change,
        bad_rep_count_change=bad_rep_count_change,
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


def _safe_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
