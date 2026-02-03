"""GymGuardian MVP app entrypoint."""

from __future__ import annotations

from datetime import datetime
import time

import cv2
import numpy as np

from analysis.squat import SquatRepCounter, SquatStateAnalyzer
from core.config import SQUAT_CONFIG
from core.paths import SESSIONS_DIR
from pose.detector import PoseDetector
from session.browser import (
    list_recent_sessions,
    open_session_folder,
    open_session_video,
)
from session.recorder import SessionRecorder
from session.summary import SessionSummary
from ui.overlay import OverlayRenderer


WINDOW_NAME = "GymGuardian"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
STATE_DASHBOARD = "dashboard"
STATE_SESSION = "session"
STATE_BROWSE = "browse"
UP_KEY = 2490368
DOWN_KEY = 2621440


def _blank_screen() -> np.ndarray:
    return np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)


def run_session(overlay: OverlayRenderer) -> None:
    """Run one workout session and persist outputs on exit."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Warning: could not open webcam for session.")
        return

    # Request 720p capture when supported by the camera.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)

    detector = PoseDetector()
    analyzer = SquatStateAnalyzer()
    rep_counter = SquatRepCounter()
    summary = SessionSummary(started_at=datetime.now())
    session_dir = SESSIONS_DIR / summary.started_at.strftime("%Y%m%d_%H%M%S")
    recorder = SessionRecorder(session_dir)
    recorder_started = False
    start_time = time.time()
    debug_enabled = False
    fps_estimate = 0.0
    previous_frame_time = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if not recorder_started:
                frame_size = (frame.shape[1], frame.shape[0])
                capture_fps = cap.get(cv2.CAP_PROP_FPS)
                recorder.start(frame_size=frame_size, fps=capture_fps)
                recorder_started = True

            timestamp = time.time()
            if previous_frame_time > 0:
                delta = timestamp - previous_frame_time
                if delta > 0:
                    instant_fps = 1.0 / delta
                    fps_estimate = instant_fps if fps_estimate == 0 else (0.9 * fps_estimate + 0.1 * instant_fps)
            previous_frame_time = timestamp

            results = detector.process(frame)
            squat_state = analyzer.classify(results)
            rep_update = rep_counter.update(squat_state, timestamp)

            elapsed = timestamp - start_time
            if rep_update.rep_started:
                summary.record_rep_start(elapsed)
            if rep_update.rep_completed:
                summary.record_rep_complete(elapsed, reason=rep_update.reason)

            summary.rep_count = rep_counter.rep_count
            summary.bad_rep_count = rep_counter.bad_rep_count

            overlay.draw(frame, results, squat_state, rep_counter)
            if debug_enabled:
                pose_detected = bool(
                    results
                    and getattr(results, "pose_landmarks", None)
                    and len(results.pose_landmarks) > 0
                )
                debug_info = {
                    "fps": fps_estimate,
                    "pose_detected": pose_detected,
                    "knee_angle": squat_state.knee_angle,
                    "down_knee_angle": SQUAT_CONFIG.down_knee_angle,
                    "up_knee_angle": SQUAT_CONFIG.up_knee_angle,
                    "shallow_knee_angle": SQUAT_CONFIG.shallow_knee_angle,
                    "down_hold_frames": SQUAT_CONFIG.down_hold_frames,
                    "min_rep_seconds": SQUAT_CONFIG.min_rep_seconds,
                }
                overlay.draw_debug(frame, debug_info)
            recorder.write(frame)

            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            if key in (ord("d"), ord("D")):
                debug_enabled = not debug_enabled
    finally:
        summary.rep_count = rep_counter.rep_count
        summary.bad_rep_count = rep_counter.bad_rep_count
        saved_path = summary.save(session_dir)
        recorder.stop()

        detector.close()
        cap.release()

        print(f"Session summary saved: {saved_path}")
        if recorder_started and recorder.output_path.exists():
            print(f"Session video path: {recorder.output_path}")


def run_browser(overlay: OverlayRenderer) -> None:
    """Render session browser and handle navigation/actions."""
    sessions = list_recent_sessions(SESSIONS_DIR)
    selected_index = 0

    while True:
        frame = _blank_screen()
        overlay.draw_browser(frame, sessions, selected_index)
        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKeyEx(0)
        if key == 8:  # Backspace
            return
        if key == UP_KEY and sessions:
            selected_index = max(0, selected_index - 1)
        elif key == DOWN_KEY and sessions:
            selected_index = min(len(sessions) - 1, selected_index + 1)
        elif key in (ord("p"), ord("P")) and sessions:
            open_session_video(sessions[selected_index])
        elif key in (ord("o"), ord("O")) and sessions:
            open_session_folder(sessions[selected_index])


def main() -> None:
    overlay = OverlayRenderer()
    state = STATE_DASHBOARD
    cv2.namedWindow(WINDOW_NAME)

    try:
        while True:
            if state == STATE_DASHBOARD:
                frame = _blank_screen()
                overlay.draw_dashboard(frame)
                cv2.imshow(WINDOW_NAME, frame)
                key = cv2.waitKeyEx(0)

                if key in (ord("s"), ord("S")):
                    state = STATE_SESSION
                elif key in (ord("b"), ord("B")):
                    state = STATE_BROWSE
                elif key in (ord("q"), ord("Q"), 27):
                    break
            elif state == STATE_SESSION:
                run_session(overlay)
                state = STATE_DASHBOARD
            elif state == STATE_BROWSE:
                run_browser(overlay)
                state = STATE_DASHBOARD
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
