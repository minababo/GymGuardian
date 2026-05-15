"""Automated tests for session summary evidence outputs."""

from __future__ import annotations

import csv
import json
from datetime import datetime

from session.summary import SessionSummary


def test_session_summary_saves_valid_json_csv_and_text_report(tmp_path) -> None:
    summary = SessionSummary(started_at=datetime(2026, 5, 9, 10, 30, 0))
    summary.add_pose_metrics(knee_angle=95.0, ankle_angle=82.0, torso_angle=12.0)
    summary.add_fps_sample(18.0)
    summary.record_rep_start(1.0)
    summary.record_rep_complete(2.0, reason="too_shallow")
    summary.record_completed_rep(
        rep_index=1,
        timestamp=2.0,
        is_bad=True,
        issues=["too_shallow"],
        min_knee_angle=118.0,
        min_ankle_angle=86.0,
        max_torso_angle=18.0,
    )
    summary.record_issue("too_shallow")
    summary.rep_count = 1
    summary.bad_rep_count = 1

    summary_path = summary.save(tmp_path)

    data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert data["valid_session"] is True
    assert data["rep_count"] == 1
    assert data["bad_rep_count"] == 1
    assert data["most_common_issue"] == "too_shallow"
    assert data["avg_fps"] == 18.0

    with (tmp_path / "rep_metrics.csv").open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["rep_index"] == "1"
    assert rows[0]["is_bad"] == "1"
    assert rows[0]["issues"] == "too_shallow"

    report_text = (tmp_path / "session_report.txt").read_text(encoding="utf-8")
    assert "Session status: valid" in report_text
    assert "Focus area: Knee bend depth" in report_text


def test_zero_rep_summary_is_marked_incomplete(tmp_path) -> None:
    summary = SessionSummary(started_at=datetime(2026, 5, 9, 10, 30, 0))

    summary_path = summary.save(tmp_path)

    data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert data["valid_session"] is False
    assert data["rep_count"] == 0
    assert "Session status: incomplete" in (tmp_path / "session_report.txt").read_text(
        encoding="utf-8"
    )
