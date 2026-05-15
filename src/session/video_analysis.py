"""Offline local-video analysis using the live squat-analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import time
from typing import Callable

import cv2

from analysis.squat import SquatRepCounter, SquatStateAnalyzer
from core.paths import INPUT_VIDEOS_DIR, SESSIONS_DIR
from core.user_profile import load_calibration_profile, load_squat_config
from pose.detector import PoseDetector
from session.feedback import current_feedback, rep_feedback
from session.summary import SessionSummary
from ui.overlay import OverlayRenderer


SUPPORTED_VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".m4v")
FEEDBACK_HOLD_SECONDS = 2.0


@dataclass(frozen=True)
class VideoAnalysisResult:
    success: bool
    message: str
    keep_running: bool = True
    source_video_path: Path | None = None
    session_dir: Path | None = None
    summary_path: Path | None = None
    analysed_video_path: Path | None = None


def find_latest_input_video(input_dir: Path = INPUT_VIDEOS_DIR) -> Path | None:
    """Return the newest supported video in the local input folder."""
    input_dir.mkdir(parents=True, exist_ok=True)
    videos = [
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
    ]
    if not videos:
        return None
    return max(videos, key=lambda path: (path.stat().st_mtime, path.name.lower()))


def analyze_video_file(
    video_path: Path,
    overlay: OverlayRenderer,
    *,
    show_frame: Callable[[object], None],
    poll_key: Callable[[int], int | None],
) -> VideoAnalysisResult:
    """Process a local video and save annotated evidence under sessions/video_*."""
    if not video_path.exists():
        return VideoAnalysisResult(
            success=False,
            message=f"Video not found: {video_path}",
            source_video_path=video_path,
        )

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        cap.release()
        return VideoAnalysisResult(
            success=False,
            message=f"Could not open video: {video_path.name}",
            source_video_path=video_path,
        )

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    fps = source_fps if source_fps and source_fps > 1 else 30.0
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if frame_w <= 0 or frame_h <= 0:
        ok, sample = cap.read()
        if not ok:
            cap.release()
            return VideoAnalysisResult(
                success=False,
                message=f"No readable frames in video: {video_path.name}",
                source_video_path=video_path,
            )
        frame_h, frame_w = sample.shape[:2]
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    started_at = datetime.now()
    session_dir = _unique_video_session_dir(started_at)
    analysed_video_path = session_dir / "analysed_video.mp4"
    session_dir.mkdir(parents=True, exist_ok=True)

    writer = cv2.VideoWriter(
        str(analysed_video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (frame_w, frame_h),
    )
    writer_enabled = writer.isOpened()
    if not writer_enabled:
        print("Warning: failed to initialize analysed video writer. Summary will still be saved.")

    detector = PoseDetector()
    calibration_profile = load_calibration_profile()
    squat_config = (
        calibration_profile.to_squat_config()
        if calibration_profile is not None
        else load_squat_config()
    )
    analyzer = SquatStateAnalyzer(squat_config)
    rep_counter = SquatRepCounter(squat_config)
    summary = SessionSummary(started_at=started_at)
    feedback_message: str | None = None
    feedback_level = "info"
    feedback_until = 0.0
    frame_index = 0
    previous_processing_time = 0.0
    processing_fps = 0.0
    keep_running = True
    cancelled = False

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame_time = frame_index / fps
            processing_now = time.time()
            if previous_processing_time > 0:
                delta = processing_now - previous_processing_time
                if delta > 0:
                    instant_fps = 1.0 / delta
                    processing_fps = (
                        instant_fps
                        if processing_fps == 0
                        else (0.9 * processing_fps + 0.1 * instant_fps)
                    )
            previous_processing_time = processing_now
            summary.add_fps_sample(processing_fps)

            timestamp_ms = int(frame_time * 1000)
            results = detector.process(frame, timestamp_ms=timestamp_ms)
            squat_state = analyzer.classify(results)
            rep_update = rep_counter.update(squat_state, frame_time)

            summary.add_pose_metrics(
                knee_angle=squat_state.knee_angle,
                ankle_angle=squat_state.ankle_angle,
                torso_angle=squat_state.torso_angle,
            )

            if rep_update.rep_started:
                summary.record_rep_start(frame_time)
            if rep_update.rep_completed:
                summary.record_rep_complete(frame_time, reason=rep_update.reason)
                summary.record_completed_rep(
                    rep_index=rep_counter.rep_count,
                    timestamp=frame_time,
                    start_timestamp=rep_update.rep_start_time or frame_time,
                    is_bad=rep_update.is_bad,
                    issues=rep_update.issues,
                    min_knee_angle=rep_update.min_knee_angle,
                    min_ankle_angle=rep_update.min_ankle_angle,
                    max_torso_angle=rep_update.max_torso_angle,
                )
                summary.record_issues(rep_update.issues)
                feedback_message, feedback_level = rep_feedback(
                    rep_update.issues,
                    rep_update.is_bad,
                )
                feedback_until = frame_time + FEEDBACK_HOLD_SECONDS

            summary.rep_count = rep_counter.rep_count
            summary.bad_rep_count = rep_counter.bad_rep_count

            feedback_text, feedback_kind = current_feedback(
                squat_state,
                feedback_message,
                feedback_level,
                feedback_until,
                frame_time,
                squat_config,
                is_in_rep=rep_counter.in_rep,
            )
            overlay.draw(
                frame,
                results,
                squat_state,
                rep_counter,
                feedback_text,
                feedback_kind,
                calibration_profile,
            )

            if writer_enabled:
                writer.write(frame)
            show_frame(frame)

            key = poll_key(1)
            if key is None:
                keep_running = False
                break
            if key == 27:
                cancelled = True
                break

            frame_index += 1
    finally:
        summary.rep_count = rep_counter.rep_count
        summary.bad_rep_count = rep_counter.bad_rep_count
        summary_path = summary.save(session_dir)
        if writer_enabled:
            writer.release()
        from session.bad_rep_export import run_bad_rep_export
        run_bad_rep_export(
            session_dir,
            analysed_video_path if writer_enabled else None,
            summary,
            fps,
            source_video_path=video_path,
        )
        detector.close()
        cap.release()

    prefix = "Video analysis cancelled and saved" if cancelled else "Video analysis saved"
    return VideoAnalysisResult(
        success=True,
        message=f"{prefix}: {session_dir.name}",
        keep_running=keep_running,
        source_video_path=video_path,
        session_dir=session_dir,
        summary_path=summary_path,
        analysed_video_path=analysed_video_path if writer_enabled else None,
    )


def _unique_video_session_dir(started_at: datetime) -> Path:
    base_name = f"video_{started_at.strftime('%Y%m%d_%H%M%S')}"
    session_dir = SESSIONS_DIR / base_name
    suffix = 1
    while session_dir.exists():
        session_dir = SESSIONS_DIR / f"{base_name}_{suffix}"
        suffix += 1
    return session_dir
