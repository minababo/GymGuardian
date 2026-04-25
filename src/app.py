"""GymGuardian MVP app entrypoint."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime
import os
import time

import cv2
import numpy as np

from analysis.squat import SquatRepCounter, SquatStateAnalyzer
from core.config import SQUAT_CONFIG
from core.paths import SESSIONS_DIR
from pose.detector import PoseDetector
from session.browser import (
    list_recent_sessions,
    load_analytics_snapshot,
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
STATE_ANALYTICS = "analytics"
UP_KEY = 2490368
DOWN_KEY = 2621440
FEEDBACK_HOLD_SECONDS = 2.0
SW_MAXIMIZE = 3

_WINDOW_MAXIMIZED = False


def _get_window_client_size(window_name: str) -> tuple[int, int] | None:
    """Return the drawable client area for the app window."""
    if os.name == "nt":
        hwnd = ctypes.windll.user32.FindWindowW(None, window_name)
        if hwnd:
            rect = wintypes.RECT()
            if ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect)):
                window_w = rect.right - rect.left
                window_h = rect.bottom - rect.top
                if window_w > 0 and window_h > 0:
                    return window_w, window_h

    try:
        _, _, window_w, window_h = cv2.getWindowImageRect(window_name)
        if window_w > 0 and window_h > 0:
            return window_w, window_h
    except cv2.error:
        pass

    return None


def _blank_screen() -> np.ndarray:
    window_size = _get_window_client_size(WINDOW_NAME)
    if window_size is not None:
        window_w, window_h = window_size
        canvas = np.empty((window_h, window_w, 3), dtype=np.uint8)
        canvas[:] = (15, 15, 15)
        return canvas

    canvas = np.empty((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    canvas[:] = (15, 15, 15)
    return canvas


def _maximize_window(window_name: str) -> None:
    """Start the app maximized while preserving standard OS window controls."""
    if os.name != "nt":
        return

    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, window_name)
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)
    except Exception:
        # Fall back to the default OpenCV window behavior if maximize fails.
        return


def _fit_frame_to_window(window_name: str, frame: np.ndarray) -> np.ndarray:
    """Letterbox frames so window resizing never stretches the content."""
    window_size = _get_window_client_size(window_name)
    if window_size is None:
        return frame

    window_w, window_h = window_size

    frame_h, frame_w = frame.shape[:2]
    scale = min(window_w / frame_w, window_h / frame_h)
    if scale <= 0:
        return frame

    target_w = max(1, int(frame_w * scale))
    target_h = max(1, int(frame_h * scale))
    if (
        target_w == frame_w
        and target_h == frame_h
        and window_w == frame_w
        and window_h == frame_h
    ):
        return frame

    resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.empty((window_h, window_w, 3), dtype=frame.dtype)
    canvas[:] = (15, 15, 15)
    x_offset = (window_w - target_w) // 2
    y_offset = (window_h - target_h) // 2
    canvas[y_offset:y_offset + target_h, x_offset:x_offset + target_w] = resized
    return canvas


def _show_frame(window_name: str, frame: np.ndarray) -> None:
    """Display a frame with aspect-preserving scaling and maximize once on startup."""
    global _WINDOW_MAXIMIZED

    cv2.imshow(window_name, _fit_frame_to_window(window_name, frame))

    if not _WINDOW_MAXIMIZED:
        _maximize_window(window_name)
        _WINDOW_MAXIMIZED = True


def _current_feedback(
    squat_state,
    feedback_message: str | None,
    feedback_level: str,
    feedback_until: float,
    timestamp: float,
) -> tuple[str | None, str]:
    if feedback_message and timestamp <= feedback_until:
        return feedback_message, feedback_level

    angle = squat_state.knee_angle
    if (
        angle is not None
        and SQUAT_CONFIG.shallow_knee_angle < angle <= SQUAT_CONFIG.rep_bottom_knee_angle
    ):
        return "Go deeper", "warning"

    return None, "info"


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
    feedback_message: str | None = None
    feedback_level = "info"
    feedback_until = 0.0

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
                    fps_estimate = (
                        instant_fps
                        if fps_estimate == 0
                        else (0.9 * fps_estimate + 0.1 * instant_fps)
                    )
            previous_frame_time = timestamp

            results = detector.process(frame)
            squat_state = analyzer.classify(results)
            rep_update = rep_counter.update(squat_state, timestamp)

            if squat_state.knee_angle is not None:
                summary.add_knee_angle(squat_state.knee_angle)

            elapsed = timestamp - start_time
            if rep_update.rep_started:
                summary.record_rep_start(elapsed)
            if rep_update.rep_completed:
                summary.record_rep_complete(elapsed, reason=rep_update.reason)
                if rep_update.reason:
                    summary.record_issue(rep_update.reason)
                if rep_update.reason == "too_shallow":
                    feedback_message = "Bad rep: too shallow"
                    feedback_level = "bad"
                else:
                    feedback_message = "Rep accepted"
                    feedback_level = "ok"
                feedback_until = timestamp + FEEDBACK_HOLD_SECONDS

            summary.rep_count = rep_counter.rep_count
            summary.bad_rep_count = rep_counter.bad_rep_count

            feedback_text, feedback_kind = _current_feedback(
                squat_state,
                feedback_message,
                feedback_level,
                feedback_until,
                timestamp,
            )
            overlay.draw(
                frame,
                results,
                squat_state,
                rep_counter,
                feedback_text,
                feedback_kind,
            )
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
                    "rep_bottom_knee_angle": SQUAT_CONFIG.rep_bottom_knee_angle,
                    "shallow_knee_angle": SQUAT_CONFIG.shallow_knee_angle,
                    "down_hold_frames": SQUAT_CONFIG.down_hold_frames,
                    "min_rep_seconds": SQUAT_CONFIG.min_rep_seconds,
                }
                overlay.draw_debug(frame, debug_info)
            recorder.write(frame)

            _show_frame(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
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
        _show_frame(WINDOW_NAME, frame)

        key = cv2.waitKeyEx(0)
        if key == 27:
            return
        if key == UP_KEY and sessions:
            selected_index = max(0, selected_index - 1)
        elif key == DOWN_KEY and sessions:
            selected_index = min(len(sessions) - 1, selected_index + 1)
        elif key in (ord("p"), ord("P")) and sessions:
            open_session_video(sessions[selected_index])
        elif key in (ord("o"), ord("O")) and sessions:
            open_session_folder(sessions[selected_index])


def run_analytics(overlay: OverlayRenderer) -> None:
    """Render lightweight session analytics using saved summaries."""
    snapshot = load_analytics_snapshot(SESSIONS_DIR)

    while True:
        frame = _blank_screen()
        overlay.draw_analytics(frame, snapshot)
        _show_frame(WINDOW_NAME, frame)

        key = cv2.waitKeyEx(0)
        if key == 27:
            return
        if key in (ord("r"), ord("R")):
            snapshot = load_analytics_snapshot(SESSIONS_DIR)


def main() -> None:
    overlay = OverlayRenderer()
    state = STATE_DASHBOARD
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, FRAME_WIDTH, FRAME_HEIGHT)

    try:
        while True:
            if state == STATE_DASHBOARD:
                frame = _blank_screen()
                overlay.draw_dashboard(frame)
                _show_frame(WINDOW_NAME, frame)
                key = cv2.waitKeyEx(0)

                if key in (ord("s"), ord("S")):
                    state = STATE_SESSION
                elif key in (ord("b"), ord("B")):
                    state = STATE_BROWSE
                elif key in (ord("a"), ord("A")):
                    state = STATE_ANALYTICS
                elif key == 27:
                    break
            elif state == STATE_SESSION:
                run_session(overlay)
                state = STATE_DASHBOARD
            elif state == STATE_BROWSE:
                run_browser(overlay)
                state = STATE_DASHBOARD
            elif state == STATE_ANALYTICS:
                run_analytics(overlay)
                state = STATE_DASHBOARD
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
