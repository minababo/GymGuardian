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


def list_recent_sessions(sessions_dir: Path, limit: int = 30) -> list[SessionBrowserItem]:
    """Return saved sessions sorted newest-first by timestamp folder name."""
    if not sessions_dir.exists():
        return []

    folders = [path for path in sessions_dir.iterdir() if path.is_dir()]
    folders.sort(key=lambda path: path.name, reverse=True)

    items: list[SessionBrowserItem] = []
    for folder in folders[:limit]:
        summary_path = folder / "summary.json"
        video_path = folder / "session.mp4"
        rep_count = None
        bad_rep_count = None

        if summary_path.exists():
            try:
                with summary_path.open("r", encoding="utf-8") as file:
                    data = json.load(file)
                rep_count = _safe_int(data.get("rep_count"))
                bad_rep_count = _safe_int(data.get("bad_rep_count"))
            except (json.JSONDecodeError, OSError):
                pass

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


def _safe_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
