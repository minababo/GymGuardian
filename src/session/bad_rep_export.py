"""Post-session export: slow-motion bad-rep clips (OpenCV) and chapter metadata (FFmpeg)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import cv2

from session.summary import CompletedRep, SessionSummary

_BUFFER_SEC = 0.5


def run_bad_rep_export(
    session_dir: Path,
    video_path: Optional[Path],
    summary: SessionSummary,
    fps: float,
    source_video_path: Optional[Path] = None,
) -> None:
    """Generate slow-motion bad-rep clips and embed chapter markers after a session.

    Called automatically after every session save.  Does nothing if there are no bad
    reps or the session video is unavailable.  FFmpeg chapter embedding is attempted
    after clip generation; if FFmpeg is not on PATH a warning is printed and the
    original video is left unchanged.

    source_video_path: if provided and exists, clips are extracted from this video
    instead of video_path (useful when video_path has the UI overlay baked in).
    """
    bad_reps = [r for r in summary.completed_reps if r.is_bad or bool(r.issues)]
    if not bad_reps:
        return

    if video_path is None or not video_path.exists():
        print(
            f"[bad_rep_export] Video not found - skipping clip extraction: {video_path}"
        )
        return

    clip_source = (
        source_video_path
        if source_video_path is not None and source_video_path.exists()
        else video_path
    )
    _generate_slow_clips(session_dir, clip_source, bad_reps, fps)

    total_sec = _video_duration_sec(video_path, fps)
    bad_rep_timestamps = [
        {
            "rep_number": r.rep_index,
            "issue": r.issues[0] if r.issues else "unknown",
            "start_sec": round(r.start_timestamp, 2),
            "end_sec": round(r.timestamp, 2),
        }
        for r in bad_reps
    ]
    _embed_chapters(video_path, bad_rep_timestamps, total_sec)


# ---------------------------------------------------------------------------
# Feature B — slow-motion clips
# ---------------------------------------------------------------------------

def _generate_slow_clips(
    session_dir: Path,
    video_path: Path,
    bad_reps: list[CompletedRep],
    fps: float,
) -> None:
    clips_dir = session_dir / "bad_reps"
    clips_dir.mkdir(exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(
            f"[bad_rep_export] Cannot open video for clip extraction: {video_path}"
        )
        cap.release()
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    for rep in bad_reps:
        issue_tag = rep.issues[0] if rep.issues else "unknown"
        out_path = clips_dir / f"bad_rep_{rep.rep_index}_{issue_tag}.mp4"
        _write_slow_clip(
            video_path=video_path,
            out_path=out_path,
            rep=rep,
            fps=fps,
            frame_size=(w, h),
            total_frames=total_frames,
        )
        print(f"[bad_rep_export] Saved clip: {out_path.name}")


def _write_slow_clip(
    video_path: Path,
    out_path: Path,
    rep: CompletedRep,
    fps: float,
    frame_size: tuple[int, int],
    total_frames: int,
) -> None:
    """Write a clip for one bad rep: 0.5 s pre-buffer + 0.25x slow-mo + 0.5 s post-buffer.

    The bad-rep portion is slowed by writing each frame four times.  A text banner
    showing the rep number, issue type, and minimum knee angle is drawn on every
    frame of the clip.
    """
    clip_start = max(0.0, rep.start_timestamp - _BUFFER_SEC)
    clip_end = min(total_frames / fps, rep.timestamp + _BUFFER_SEC)

    clip_start_frame = int(clip_start * fps)
    rep_start_frame = int(rep.start_timestamp * fps)
    rep_end_frame = int(rep.timestamp * fps)
    clip_end_frame = min(total_frames - 1, int(clip_end * fps))

    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, clip_start_frame)

    writer = cv2.VideoWriter(
        str(out_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        frame_size,
    )

    issue_label = rep.issues[0] if rep.issues else "unknown"
    all_issues = ", ".join(rep.issues) if rep.issues else "none"
    angle_label = (
        f"Min knee: {rep.min_knee_angle:.1f} deg"
        if rep.min_knee_angle is not None
        else ""
    )
    banner_lines = [f"Rep {rep.rep_index} - {issue_label}", f"Issues: {all_issues}"]
    if angle_label:
        banner_lines.append(angle_label)

    for frame_idx in range(clip_start_frame, clip_end_frame + 1):
        ok, frame = cap.read()
        if not ok:
            break

        _draw_banner(frame, banner_lines)

        repeat = 4 if rep_start_frame <= frame_idx < rep_end_frame else 1
        for _ in range(repeat):
            writer.write(frame)

    cap.release()
    writer.release()


def _draw_banner(frame, lines: list[str]) -> None:
    y = 30
    for line in lines:
        cv2.putText(
            frame, line, (10, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3, cv2.LINE_AA,
        )
        cv2.putText(
            frame, line, (10, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA,
        )
        y += 28


# ---------------------------------------------------------------------------
# Feature A — FFmpeg chapter embedding
# ---------------------------------------------------------------------------

def _embed_chapters(
    video_path: Path,
    bad_rep_timestamps: list[dict],
    total_sec: float,
) -> None:
    """Embed FFMETADATA1 chapter markers into video_path in-place via FFmpeg.

    Skips gracefully if FFmpeg is not installed — prints a console warning and
    leaves the original file unchanged.
    """
    if not shutil.which("ffmpeg"):
        print(
            "[bad_rep_export] FFmpeg not found — chapter markers skipped. "
            "Install FFmpeg (e.g. winget install ffmpeg) to enable chapter embedding."
        )
        return

    total_ms = int(total_sec * 1000)
    chapters: list[tuple[int, int, str]] = [(0, total_ms, "Session Start")]
    for entry in sorted(bad_rep_timestamps, key=lambda e: e["start_sec"]):
        start_ms = int(entry["start_sec"] * 1000)
        end_ms = int(entry["end_sec"] * 1000)
        title = f"Rep {entry['rep_number']} — {entry['issue']}"
        chapters.append((start_ms, end_ms, title))
    chapters.append((total_ms, total_ms, "Session End"))

    metadata_text = build_ffmetadata_string(chapters)

    with tempfile.TemporaryDirectory() as tmp:
        meta_path = Path(tmp) / "chapters.ffmetadata"
        meta_path.write_text(metadata_text, encoding="utf-8")
        out_path = Path(tmp) / "chaptered.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(meta_path),
            "-map_metadata", "1",
            "-codec", "copy",
            str(out_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                err = result.stderr.decode(errors="replace")[:300]
                print(f"[bad_rep_export] FFmpeg chapter embed failed: {err}")
                return
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            print(f"[bad_rep_export] FFmpeg chapter embed error: {exc}")
            return

        out_path.replace(video_path)
        print(f"[bad_rep_export] Chapter markers embedded into: {video_path.name}")


def build_ffmetadata_string(chapters: list[tuple[int, int, str]]) -> str:
    """Build an FFMETADATA1 chapter string from (start_ms, end_ms, title) tuples.

    Exposed as a public function so it can be tested without a video file.
    """
    lines = [";FFMETADATA1", ""]
    for start_ms, end_ms, title in chapters:
        lines += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={start_ms}",
            f"END={end_ms}",
            f"title={title}",
            "",
        ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _video_duration_sec(video_path: Path, fallback_fps: float) -> float:
    cap = cv2.VideoCapture(str(video_path))
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    file_fps = cap.get(cv2.CAP_PROP_FPS) or fallback_fps
    cap.release()
    return frames / file_fps if file_fps > 0 else 0.0
