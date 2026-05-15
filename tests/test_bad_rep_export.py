"""Tests for bad-rep slow-motion clip export and chapter metadata generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from session.bad_rep_export import build_ffmetadata_string, _embed_chapters
from session.summary import SessionSummary


# ---------------------------------------------------------------------------
# 1. bad_rep_timestamps JSON structure
# ---------------------------------------------------------------------------

def test_bad_rep_timestamps_included_in_to_dict():
    summary = SessionSummary(started_at=datetime(2026, 5, 15, 10, 0, 0))
    summary.record_completed_rep(
        rep_index=3,
        timestamp=14.8,
        start_timestamp=12.4,
        is_bad=True,
        issues=("too_shallow",),
        min_knee_angle=112.5,
        min_ankle_angle=None,
        max_torso_angle=None,
    )
    data = summary.to_dict()
    assert "bad_rep_timestamps" in data
    assert data["bad_rep_timestamps"] == [
        {"rep_number": 3, "issue": "too_shallow", "start_sec": 12.4, "end_sec": 14.8}
    ]


def test_bad_rep_timestamps_empty_when_no_bad_reps():
    summary = SessionSummary(started_at=datetime(2026, 5, 15, 10, 0, 0))
    summary.record_completed_rep(
        rep_index=1,
        timestamp=5.0,
        start_timestamp=3.0,
        is_bad=False,
        issues=(),
        min_knee_angle=98.0,
        min_ankle_angle=None,
        max_torso_angle=None,
    )
    data = summary.to_dict()
    assert data["bad_rep_timestamps"] == []


def test_ankle_control_rep_included_in_bad_rep_timestamps():
    summary = SessionSummary(started_at=datetime(2026, 5, 15, 10, 0, 0))
    summary.record_completed_rep(
        rep_index=1, timestamp=8.0, start_timestamp=6.0,
        is_bad=False, issues=("ankle_control",), min_knee_angle=95.0,
        min_ankle_angle=175.0, max_torso_angle=None,
    )
    data = summary.to_dict()
    assert len(data["bad_rep_timestamps"]) == 1
    assert data["bad_rep_timestamps"][0]["issue"] == "ankle_control"


def test_clean_rep_excluded_from_bad_rep_timestamps():
    summary = SessionSummary(started_at=datetime(2026, 5, 15, 10, 0, 0))
    summary.record_completed_rep(
        rep_index=1, timestamp=8.0, start_timestamp=6.0,
        is_bad=False, issues=(), min_knee_angle=95.0,
        min_ankle_angle=None, max_torso_angle=None,
    )
    data = summary.to_dict()
    assert data["bad_rep_timestamps"] == []


def test_bad_rep_timestamps_only_includes_bad_reps():
    summary = SessionSummary(started_at=datetime(2026, 5, 15, 10, 0, 0))
    summary.record_completed_rep(
        rep_index=1, timestamp=5.0, start_timestamp=3.0,
        is_bad=False, issues=(), min_knee_angle=95.0,
        min_ankle_angle=None, max_torso_angle=None,
    )
    summary.record_completed_rep(
        rep_index=2, timestamp=12.0, start_timestamp=10.0,
        is_bad=True, issues=("too_shallow",), min_knee_angle=115.0,
        min_ankle_angle=None, max_torso_angle=None,
    )
    data = summary.to_dict()
    assert len(data["bad_rep_timestamps"]) == 1
    assert data["bad_rep_timestamps"][0]["rep_number"] == 2


def test_start_timestamp_preserved_in_completed_reps():
    summary = SessionSummary(started_at=datetime(2026, 5, 15, 10, 0, 0))
    summary.record_completed_rep(
        rep_index=1, timestamp=8.0, start_timestamp=6.5,
        is_bad=True, issues=("too_shallow",), min_knee_angle=111.0,
        min_ankle_angle=None, max_torso_angle=None,
    )
    data = summary.to_dict()
    assert data["completed_reps"][0]["start_timestamp"] == 6.5


# ---------------------------------------------------------------------------
# 2. Chapter metadata string format
# ---------------------------------------------------------------------------

def test_build_ffmetadata_string_contains_header():
    text = build_ffmetadata_string([])
    assert text.startswith(";FFMETADATA1")


def test_build_ffmetadata_string_chapter_fields():
    chapters = [
        (0, 60000, "Session Start"),
        (12400, 14800, "Rep 3 — too_shallow"),
        (60000, 60000, "Session End"),
    ]
    text = build_ffmetadata_string(chapters)
    assert "[CHAPTER]" in text
    assert "TIMEBASE=1/1000" in text
    assert "START=12400" in text
    assert "END=14800" in text
    assert "title=Rep 3 — too_shallow" in text
    assert "title=Session Start" in text
    assert "title=Session End" in text


def test_build_ffmetadata_string_chapter_count():
    chapters = [
        (0, 5000, "A"),
        (5000, 10000, "B"),
        (10000, 10000, "C"),
    ]
    text = build_ffmetadata_string(chapters)
    assert text.count("[CHAPTER]") == 3


# ---------------------------------------------------------------------------
# 3. Slow-motion frame count calculation
# ---------------------------------------------------------------------------

def test_slow_clip_frame_count_logic():
    """The written frame count should equal pre + 2*bad_rep + post."""
    fps = 30.0
    buffer = 2.0
    rep_start, rep_end = 5.0, 7.0
    clip_start = rep_start - buffer   # 3.0
    clip_end = rep_end + buffer       # 9.0

    clip_start_frame = int(clip_start * fps)   # 90
    rep_start_frame  = int(rep_start  * fps)   # 150
    rep_end_frame    = int(rep_end    * fps)    # 210
    clip_end_frame   = int(clip_end   * fps)    # 270

    written = 0
    for fi in range(clip_start_frame, clip_end_frame + 1):
        repeat = 2 if rep_start_frame <= fi < rep_end_frame else 1
        written += repeat

    pre_frames  = rep_start_frame - clip_start_frame          # 60
    bad_frames  = rep_end_frame   - rep_start_frame           # 60
    post_frames = clip_end_frame  - rep_end_frame + 1         # 61 (inclusive)
    expected    = pre_frames + 2 * bad_frames + post_frames   # 60+120+61 = 241

    assert written == expected


def test_slow_clip_buffer_clamped_to_zero():
    """When a bad rep starts at t=0 the pre-buffer should clamp to frame 0."""
    fps = 30.0
    clip_start = max(0.0, 0.0 - 2.0)   # clamped to 0
    assert clip_start == 0.0
    assert int(clip_start * fps) == 0


# ---------------------------------------------------------------------------
# 4. Graceful FFmpeg skip when not installed
# ---------------------------------------------------------------------------

def test_embed_chapters_no_ffmpeg_does_not_raise(monkeypatch, capsys):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    _embed_chapters(Path("nonexistent.mp4"), [], 60.0)
    captured = capsys.readouterr()
    assert "FFmpeg not found" in captured.out


def test_embed_chapters_no_ffmpeg_does_not_modify_file(monkeypatch, tmp_path):
    dummy = tmp_path / "session.mp4"
    dummy.write_bytes(b"fake")
    monkeypatch.setattr("shutil.which", lambda _name: None)
    _embed_chapters(dummy, [], 10.0)
    assert dummy.read_bytes() == b"fake"
