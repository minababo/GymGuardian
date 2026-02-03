"""GymGuardian MVP app entrypoint."""

from __future__ import annotations

from datetime import datetime
import time

import cv2

from analysis.squat import SquatRepCounter, SquatStateAnalyzer
from core.paths import SESSIONS_DIR
from pose.detector import PoseDetector
from session.recorder import SessionRecorder
from session.summary import SessionSummary
from ui.overlay import OverlayRenderer


def main() -> None:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam at index 0.")

    # Request 720p capture when supported by the camera.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    detector = PoseDetector()
    analyzer = SquatStateAnalyzer()
    rep_counter = SquatRepCounter()
    overlay = OverlayRenderer()
    summary = SessionSummary(started_at=datetime.now())
    session_dir = SESSIONS_DIR / summary.started_at.strftime("%Y%m%d_%H%M%S")
    recorder = SessionRecorder(session_dir)
    recorder_started = False
    start_time = time.time()

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
            recorder.write(frame)

            cv2.imshow("GymGuardian", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
    finally:
        summary.rep_count = rep_counter.rep_count
        summary.bad_rep_count = rep_counter.bad_rep_count
        saved_path = summary.save(session_dir)
        recorder.stop()

        detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print(f"Session summary saved: {saved_path}")
        if recorder_started and recorder.output_path.exists():
            print(f"Session video path: {recorder.output_path}")


if __name__ == "__main__":
    main()
