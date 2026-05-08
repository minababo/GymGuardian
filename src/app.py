"""GymGuardian squat coach application entrypoint."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime
from functools import lru_cache
import os
import subprocess
import time

import cv2
import numpy as np

from analysis.squat import SquatRepCounter, SquatStateAnalyzer
from core.config import CALIBRATION_CONFIG, SquatConfig
from core.paths import SESSIONS_DIR
from core.user_profile import (
    build_calibration_profile,
    load_app_settings,
    load_calibration_profile,
    load_squat_config,
    reset_calibration_profile,
    save_calibration_profile,
    set_camera_index,
    switch_camera_index,
    toggle_hide_incomplete_sessions,
    toggle_theme,
)
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
APP_BG = (229, 237, 233)
STATE_DASHBOARD = "dashboard"
STATE_SESSION = "session"
STATE_BROWSE = "browse"
STATE_ANALYTICS = "analytics"
STATE_CALIBRATION = "calibration"
STATE_SETTINGS = "settings"
UP_KEY = 2490368
DOWN_KEY = 2621440
FEEDBACK_HOLD_SECONDS = 2.0
SW_MAXIMIZE = 3
STATIC_SCREEN_WAIT_MS = 80
CAMERA_INDICES = (0, 1, 2)
FALLBACK_CAMERA_LABELS = {
    0: "Default / built-in",
    1: "External USB",
    2: "Phone / virtual",
}

_WINDOW_MAXIMIZED = False
_LAST_CAMERA_WARNING: str | None = None


def _sync_app_background(overlay: OverlayRenderer) -> None:
    global APP_BG
    APP_BG = overlay.BG


def _get_window_client_size(window_name: str) -> tuple[int, int] | None:
    """Return the drawable client area for the app window."""
    if not _window_is_open(window_name):
        return None

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


def _window_is_open(window_name: str) -> bool:
    """Return false when the user has closed the OpenCV window."""
    try:
        return cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) >= 1
    except cv2.error:
        return False


def _wait_for_key_or_close(delay_ms: int) -> int | None:
    """Poll keyboard input while allowing the native close button to exit."""
    key = cv2.waitKeyEx(delay_ms)
    if not _window_is_open(WINDOW_NAME):
        return None
    return key


def _blank_screen() -> np.ndarray:
    window_size = _get_window_client_size(WINDOW_NAME)
    if window_size is not None:
        window_w, window_h = window_size
        canvas = np.empty((window_h, window_w, 3), dtype=np.uint8)
        canvas[:] = APP_BG
        return canvas

    canvas = np.empty((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    canvas[:] = APP_BG
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

    interpolation = (
        cv2.INTER_CUBIC
        if target_w > frame_w or target_h > frame_h
        else cv2.INTER_AREA
    )
    resized = cv2.resize(frame, (target_w, target_h), interpolation=interpolation)
    canvas = np.empty((window_h, window_w, 3), dtype=frame.dtype)
    canvas[:] = APP_BG
    x_offset = (window_w - target_w) // 2
    y_offset = (window_h - target_h) // 2
    canvas[y_offset:y_offset + target_h, x_offset:x_offset + target_w] = resized
    return canvas


def _show_frame(window_name: str, frame: np.ndarray) -> None:
    """Display a frame with aspect-preserving scaling and maximize once on startup."""
    global _WINDOW_MAXIMIZED

    if not _window_is_open(window_name):
        return

    if not _WINDOW_MAXIMIZED:
        _maximize_window(window_name)
        cv2.waitKey(1)
        _WINDOW_MAXIMIZED = True

    cv2.imshow(window_name, _fit_frame_to_window(window_name, frame))


def _initialize_window() -> None:
    """Create and maximize the window before the first real UI frame is rendered."""
    global _WINDOW_MAXIMIZED

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, FRAME_WIDTH, FRAME_HEIGHT)

    # OpenCV only creates the native window after the first imshow call.
    placeholder = np.empty((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    placeholder[:] = APP_BG
    cv2.imshow(WINDOW_NAME, placeholder)
    for _ in range(3):
        cv2.waitKey(1)

    _maximize_window(WINDOW_NAME)
    for _ in range(5):
        cv2.waitKey(1)
    _WINDOW_MAXIMIZED = True


def _current_feedback(
    squat_state,
    feedback_message: str | None,
    feedback_level: str,
    feedback_until: float,
    timestamp: float,
    squat_config: SquatConfig,
) -> tuple[str | None, str]:
    if feedback_message and timestamp <= feedback_until:
        return feedback_message, feedback_level

    angle = squat_state.knee_angle
    if (
        angle is not None
        and squat_config.shallow_knee_angle < angle <= squat_config.rep_bottom_knee_angle
    ):
        return "Go deeper", "warning"

    return None, "info"


def _rep_feedback(issues: tuple[str, ...], is_bad: bool) -> tuple[str, str]:
    if is_bad and "too_shallow" in issues:
        return "Bad rep: increase squat depth", "bad"
    if "torso_lean" in issues and "ankle_control" in issues:
        return "Rep logged: improve torso and ankle control", "warning"
    if "torso_lean" in issues:
        return "Rep logged: reduce forward torso lean", "warning"
    if "ankle_control" in issues:
        return "Rep logged: improve ankle control", "warning"
    return "Rep accepted", "ok"


def _filter_sessions_for_settings(sessions, settings):
    if not getattr(settings, "hide_incomplete_sessions", False):
        return sessions

    return [
        session
        for session in sessions
        if bool(
            getattr(
                session,
                "valid_session",
                session.rep_count not in (None, 0),
            )
        )
    ]


def _calibration_status(
    *,
    phase: str,
    sample_count: int = 0,
    elapsed: float = 0.0,
    message: str = "",
    error: str = "",
    profile=None,
) -> dict:
    return {
        "phase": phase,
        "sample_count": sample_count,
        "elapsed": elapsed,
        "duration": CALIBRATION_CONFIG.collection_seconds,
        "message": message,
        "error": error,
        "profile": profile,
    }


def _camera_backend() -> int:
    if os.name == "nt":
        return cv2.CAP_DSHOW
    return cv2.CAP_ANY


@lru_cache(maxsize=1)
def _windows_camera_names() -> tuple[str, ...]:
    """Best-effort Windows camera names for display; OpenCV still uses indices."""
    if os.name != "nt":
        return ()

    command = (
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' } | "
        "Select-Object -ExpandProperty Name"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ()

    names = []
    for line in completed.stdout.splitlines():
        name = line.strip()
        if name:
            names.append(name)
    return tuple(names)


def _camera_options() -> list[dict[str, object]]:
    detected_names = _windows_camera_names()
    options = []
    for index in CAMERA_INDICES:
        label = (
            detected_names[index]
            if index < len(detected_names)
            else FALLBACK_CAMERA_LABELS[index]
        )
        options.append(
            {
                "index": index,
                "label": label,
                "detected": index < len(detected_names),
            }
        )
    return options


def _configure_camera(cap: cv2.VideoCapture) -> None:
    # These are requests only; unsupported cameras keep their own defaults.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)


def _camera_has_frame(cap: cv2.VideoCapture) -> bool:
    for _ in range(5):
        ok, _frame = cap.read()
        if ok:
            return True
        time.sleep(0.03)
    return False


def _open_camera(camera_index: int, context: str) -> tuple[cv2.VideoCapture | None, int]:
    """Open the selected camera index, falling back to index 0 when needed."""
    global _LAST_CAMERA_WARNING

    requested_index = camera_index if 0 <= camera_index <= 2 else 0
    indices = [requested_index]
    if requested_index != 0:
        indices.append(0)

    for index in indices:
        cap = cv2.VideoCapture(index, _camera_backend())
        if cap.isOpened():
            _configure_camera(cap)
            if not _camera_has_frame(cap):
                cap.release()
                print(f"Warning: camera {index} opened but produced no frames for {context}.")
                continue

            if index != requested_index:
                warning = (
                    f"Warning: camera {requested_index} could not be opened for "
                    f"{context}; using camera 0 instead."
                )
                print(warning)
                _LAST_CAMERA_WARNING = warning
                set_camera_index(load_app_settings(), 0)
            else:
                _LAST_CAMERA_WARNING = None
            return cap, index

        cap.release()
        print(f"Warning: camera {index} could not be opened for {context}.")

    _LAST_CAMERA_WARNING = (
        f"Warning: camera {requested_index} could not be opened for {context}, "
        "and fallback camera 0 also failed."
    )
    print(_LAST_CAMERA_WARNING)
    return None, requested_index


def run_session(overlay: OverlayRenderer) -> bool:
    """Run one workout session and persist outputs on exit."""
    settings = load_app_settings()
    cap, _active_camera_index = _open_camera(settings.camera_index, "session")
    if cap is None:
        return _window_is_open(WINDOW_NAME)

    detector = PoseDetector()
    calibration_profile = load_calibration_profile()
    squat_config = (
        calibration_profile.to_squat_config()
        if calibration_profile is not None
        else load_squat_config()
    )
    analyzer = SquatStateAnalyzer(squat_config)
    rep_counter = SquatRepCounter(squat_config)
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
    keep_running = True

    try:
        while True:
            if not _window_is_open(WINDOW_NAME):
                keep_running = False
                break

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
            summary.add_fps_sample(fps_estimate)

            results = detector.process(frame)
            squat_state = analyzer.classify(results)
            rep_update = rep_counter.update(squat_state, timestamp)

            summary.add_pose_metrics(
                knee_angle=squat_state.knee_angle,
                ankle_angle=squat_state.ankle_angle,
                torso_angle=squat_state.torso_angle,
            )

            elapsed = timestamp - start_time
            if rep_update.rep_started:
                summary.record_rep_start(elapsed)
            if rep_update.rep_completed:
                summary.record_rep_complete(elapsed, reason=rep_update.reason)
                summary.record_completed_rep(
                    rep_index=rep_counter.rep_count,
                    timestamp=elapsed,
                    is_bad=rep_update.is_bad,
                    issues=rep_update.issues,
                    min_knee_angle=rep_update.min_knee_angle,
                    min_ankle_angle=rep_update.min_ankle_angle,
                    max_torso_angle=rep_update.max_torso_angle,
                )
                summary.record_issues(rep_update.issues)
                feedback_message, feedback_level = _rep_feedback(
                    rep_update.issues,
                    rep_update.is_bad,
                )
                feedback_until = timestamp + FEEDBACK_HOLD_SECONDS

            summary.rep_count = rep_counter.rep_count
            summary.bad_rep_count = rep_counter.bad_rep_count

            feedback_text, feedback_kind = _current_feedback(
                squat_state,
                feedback_message,
                feedback_level,
                feedback_until,
                timestamp,
                squat_config,
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
                    "ankle_angle": squat_state.ankle_angle,
                    "torso_angle": squat_state.torso_angle,
                    "down_knee_angle": squat_config.down_knee_angle,
                    "up_knee_angle": squat_config.up_knee_angle,
                    "rep_bottom_knee_angle": squat_config.rep_bottom_knee_angle,
                    "shallow_knee_angle": squat_config.shallow_knee_angle,
                    "ankle_control_angle": squat_config.ankle_control_angle,
                    "torso_lean_angle": squat_config.torso_lean_angle,
                    "down_hold_frames": squat_config.down_hold_frames,
                    "ready_standing_frames": squat_config.ready_standing_frames,
                    "min_rep_seconds": squat_config.min_rep_seconds,
                }
                overlay.draw_debug(frame, debug_info)
            recorder.write(frame)

            _show_frame(WINDOW_NAME, frame)
            key = _wait_for_key_or_close(1)
            if key is None:
                keep_running = False
                break
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
        rep_metrics_path = session_dir / "rep_metrics.csv"
        if rep_metrics_path.exists():
            print(f"Rep metrics exported: {rep_metrics_path}")
        session_report_path = session_dir / "session_report.txt"
        if session_report_path.exists():
            print(f"Session report exported: {session_report_path}")
        if recorder_started and recorder.output_path.exists():
            print(f"Session video path: {recorder.output_path}")

    return keep_running


def run_browser(overlay: OverlayRenderer) -> bool:
    """Render session browser and handle navigation/actions."""
    settings = load_app_settings()
    all_sessions = list_recent_sessions(SESSIONS_DIR)
    sessions = _filter_sessions_for_settings(all_sessions, settings)
    selected_index = 0

    while True:
        if not _window_is_open(WINDOW_NAME):
            return False
        selected_index = min(selected_index, max(0, len(sessions) - 1))

        frame = _blank_screen()
        overlay.draw_browser(
            frame,
            sessions,
            selected_index,
            settings.hide_incomplete_sessions,
        )
        _show_frame(WINDOW_NAME, frame)

        key = _wait_for_key_or_close(STATIC_SCREEN_WAIT_MS)
        if key is None:
            return False
        if key == -1:
            continue
        if key == 27:
            return True
        if key == UP_KEY and sessions:
            selected_index = max(0, selected_index - 1)
        elif key == DOWN_KEY and sessions:
            selected_index = min(len(sessions) - 1, selected_index + 1)
        elif key in (ord("p"), ord("P")) and sessions:
            open_session_video(sessions[selected_index])
        elif key in (ord("o"), ord("O")) and sessions:
            open_session_folder(sessions[selected_index])
        elif key in (ord("h"), ord("H")):
            settings = toggle_hide_incomplete_sessions(settings)
            all_sessions = list_recent_sessions(SESSIONS_DIR)
            sessions = _filter_sessions_for_settings(all_sessions, settings)
            selected_index = 0


def run_analytics(overlay: OverlayRenderer) -> bool:
    """Render lightweight session analytics using saved summaries."""
    snapshot = load_analytics_snapshot(SESSIONS_DIR)
    calibration_profile = load_calibration_profile()

    while True:
        if not _window_is_open(WINDOW_NAME):
            return False

        frame = _blank_screen()
        overlay.draw_analytics(frame, snapshot, calibration_profile)
        _show_frame(WINDOW_NAME, frame)

        key = _wait_for_key_or_close(STATIC_SCREEN_WAIT_MS)
        if key is None:
            return False
        if key == -1:
            continue
        if key == 27:
            return True
        if key in (ord("r"), ord("R")):
            snapshot = load_analytics_snapshot(SESSIONS_DIR)
            calibration_profile = load_calibration_profile()


def run_calibration(overlay: OverlayRenderer) -> bool:
    """Collect a short calibration set and save user-specific squat thresholds."""
    settings = load_app_settings()
    cap, _active_camera_index = _open_camera(settings.camera_index, "calibration")
    profile = load_calibration_profile()

    if cap is None:
        status = _calibration_status(
            phase="error",
            message="Could not open selected camera or fallback camera 0.",
            profile=profile,
        )
        while True:
            if not _window_is_open(WINDOW_NAME):
                return False
            frame = _blank_screen()
            overlay.draw_calibration(frame, None, None, status)
            _show_frame(WINDOW_NAME, frame)
            key = _wait_for_key_or_close(STATIC_SCREEN_WAIT_MS)
            if key is None:
                return False
            if key == -1:
                continue
            if key == 27:
                return True
            if key in (ord("r"), ord("R")):
                reset_calibration_profile()
                profile = None
                status = _calibration_status(
                    phase="reset",
                    message="Calibration reset. Defaults will be used.",
                    profile=profile,
                )

    detector = PoseDetector()
    analyzer = SquatStateAnalyzer()
    knee_samples: list[float] = []
    started_at = time.time()
    saved = False
    message = "Perform 2-3 normal squats. The app will save automatically."
    phase = "collecting"

    try:
        while True:
            if not _window_is_open(WINDOW_NAME):
                return False

            ok, frame = cap.read()
            if not ok:
                phase = "error"
                message = "Camera frame unavailable. Press Esc to return."
                frame = _blank_screen()
                results = None
                squat_state = None
            else:
                results = detector.process(frame)
                squat_state = analyzer.classify(results)
                if (
                    phase == "collecting"
                    and squat_state.pose_visible
                    and squat_state.knee_angle is not None
                ):
                    knee_samples.append(squat_state.knee_angle)

            elapsed = time.time() - started_at
            if (
                phase == "collecting"
                and elapsed >= CALIBRATION_CONFIG.collection_seconds
            ):
                try:
                    profile = build_calibration_profile(knee_samples)
                    save_calibration_profile(profile)
                    phase = "saved"
                    saved = True
                    message = "Calibration saved. Press Esc to return or R to reset."
                except ValueError as exc:
                    phase = "failed"
                    message = f"{exc} Press R to retry or Esc to return."

            status = _calibration_status(
                phase=phase,
                sample_count=len(knee_samples),
                elapsed=elapsed,
                message=message,
                profile=profile,
            )
            overlay.draw_calibration(frame, results, squat_state, status)
            _show_frame(WINDOW_NAME, frame)

            key = _wait_for_key_or_close(1 if phase == "collecting" else STATIC_SCREEN_WAIT_MS)
            if key is None:
                return False
            if key == -1:
                continue
            if key == 27:
                return True
            if key in (ord("r"), ord("R")):
                reset_calibration_profile()
                profile = None
                knee_samples.clear()
                started_at = time.time()
                saved = False
                phase = "collecting"
                message = "Calibration reset. Perform 2-3 normal squats again."
            elif key in (ord("c"), ord("C")) and saved:
                knee_samples.clear()
                started_at = time.time()
                saved = False
                phase = "collecting"
                message = "Recalibrating. Perform 2-3 normal squats."
    finally:
        detector.close()
        cap.release()


def run_settings(overlay: OverlayRenderer) -> bool:
    """Render local settings and handle non-destructive preferences."""
    settings = load_app_settings()

    while True:
        if not _window_is_open(WINDOW_NAME):
            return False

        frame = _blank_screen()
        overlay.draw_settings(
            frame,
            settings,
            load_calibration_profile(),
            _camera_options(),
        )
        _show_frame(WINDOW_NAME, frame)

        key = _wait_for_key_or_close(STATIC_SCREEN_WAIT_MS)
        if key is None:
            return False
        if key == -1:
            continue
        if key == 27:
            return True
        if key in (ord("t"), ord("T")):
            settings = toggle_theme(settings)
            overlay.set_theme(settings.theme)
            _sync_app_background(overlay)
        elif key in (ord("h"), ord("H")):
            settings = toggle_hide_incomplete_sessions(settings)
        elif key in (ord("k"), ord("K")):
            _windows_camera_names.cache_clear()
            settings = switch_camera_index(settings)
        elif key in (ord("r"), ord("R")):
            reset_calibration_profile()


def main() -> None:
    global _LAST_CAMERA_WARNING

    settings = load_app_settings()
    overlay = OverlayRenderer(settings.theme)
    _sync_app_background(overlay)
    state = STATE_DASHBOARD
    _initialize_window()

    try:
        while True:
            if not _window_is_open(WINDOW_NAME):
                break

            if state == STATE_DASHBOARD:
                settings = load_app_settings()
                frame = _blank_screen()
                overlay.draw_dashboard(
                    frame,
                    load_calibration_profile(),
                    settings,
                    _LAST_CAMERA_WARNING,
                    _camera_options(),
                )
                _show_frame(WINDOW_NAME, frame)
                key = _wait_for_key_or_close(STATIC_SCREEN_WAIT_MS)

                if key is None:
                    break
                if key == -1:
                    continue
                if key in (ord("s"), ord("S")):
                    state = STATE_SESSION
                elif key in (ord("c"), ord("C")):
                    state = STATE_CALIBRATION
                elif key in (ord("b"), ord("B")):
                    state = STATE_BROWSE
                elif key in (ord("a"), ord("A")):
                    state = STATE_ANALYTICS
                elif key in (ord("g"), ord("G")):
                    state = STATE_SETTINGS
                elif key in (ord("k"), ord("K")):
                    _windows_camera_names.cache_clear()
                    settings = switch_camera_index(settings)
                    _LAST_CAMERA_WARNING = None
                elif key == 27:
                    break
            elif state == STATE_SESSION:
                if not run_session(overlay):
                    break
                state = STATE_DASHBOARD
            elif state == STATE_BROWSE:
                if not run_browser(overlay):
                    break
                state = STATE_DASHBOARD
            elif state == STATE_ANALYTICS:
                if not run_analytics(overlay):
                    break
                state = STATE_DASHBOARD
            elif state == STATE_CALIBRATION:
                if not run_calibration(overlay):
                    break
                state = STATE_DASHBOARD
            elif state == STATE_SETTINGS:
                if not run_settings(overlay):
                    break
                state = STATE_DASHBOARD
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
