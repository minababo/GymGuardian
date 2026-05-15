"""Automated tests for saved-session analytics loading."""

from __future__ import annotations

import json
from pathlib import Path

from session.browser import list_recent_sessions, load_analytics_snapshot


def _write_summary(sessions_dir: Path, folder_name: str, data: dict) -> None:
    folder = sessions_dir / folder_name
    folder.mkdir(parents=True)
    (folder / "summary.json").write_text(json.dumps(data), encoding="utf-8")


def test_analytics_uses_latest_meaningful_session_and_previous_meaningful_session(tmp_path) -> None:
    _write_summary(
        tmp_path,
        "20260503_120000",
        {"valid_session": False, "rep_count": 0, "bad_rep_count": 0},
    )
    _write_summary(
        tmp_path,
        "20260502_120000",
        {
            "valid_session": True,
            "rep_count": 10,
            "bad_rep_count": 2,
            "avg_knee_angle": 140.0,
            "min_knee_angle": 90.0,
            "avg_ankle_angle": 88.0,
            "avg_torso_angle": 10.0,
            "avg_fps": 18.0,
            "issue_counts": {"too_shallow": 2},
            "most_common_issue": "too_shallow",
        },
    )
    _write_summary(
        tmp_path,
        "20260501_120000",
        {
            "valid_session": True,
            "rep_count": 8,
            "bad_rep_count": 1,
            "avg_knee_angle": 130.0,
            "min_knee_angle": 85.0,
            "avg_ankle_angle": 84.0,
            "avg_torso_angle": 8.0,
            "avg_fps": 16.0,
            "issue_counts": {"ankle_control": 1},
            "most_common_issue": "ankle_control",
        },
    )

    snapshot = load_analytics_snapshot(tmp_path)

    assert snapshot.total_sessions == 3
    assert snapshot.meaningful_session_count == 2
    assert snapshot.latest_timestamp == "20260502_120000"
    assert snapshot.previous_timestamp == "20260501_120000"
    assert snapshot.latest_rep_count == 10
    assert snapshot.latest_bad_rep_percentage == 20.0
    assert snapshot.rep_count_change == 2
    assert snapshot.bad_rep_percentage_change == 7.5
    assert snapshot.avg_knee_angle_change == 10.0
    assert snapshot.issue_totals == {"too_shallow": 2, "ankle_control": 1}
    assert snapshot.avg_fps_overall == 17.0
    assert len(snapshot.trend_sessions) == 2


def test_session_browser_marks_incomplete_sessions_without_crashing(tmp_path) -> None:
    _write_summary(tmp_path, "20260503_120000", {"rep_count": 0, "bad_rep_count": 0})
    _write_summary(tmp_path, "20260502_120000", {"rep_count": 3, "bad_rep_count": 1})

    sessions = list_recent_sessions(tmp_path, limit=None)

    assert sessions[0].valid_session is False
    assert sessions[0].folder_name == "20260503_120000"
    assert sessions[1].valid_session is True
    assert sessions[1].folder_name == "20260502_120000"


def test_session_browser_supports_video_analysis_folders(tmp_path) -> None:
    _write_summary(tmp_path, "20260503_120000", {"rep_count": 4, "bad_rep_count": 0})
    _write_summary(tmp_path, "video_20260504_120000", {"rep_count": 5, "bad_rep_count": 1})
    analysed_video = tmp_path / "video_20260504_120000" / "analysed_video.mp4"
    analysed_video.write_bytes(b"placeholder")

    sessions = list_recent_sessions(tmp_path, limit=None)

    assert sessions[0].folder_name == "video_20260504_120000"
    assert sessions[0].video_path == analysed_video
