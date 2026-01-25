"""GymGuardian MVP app entrypoint."""

from __future__ import annotations

import cv2

from analysis.squat import SquatStateAnalyzer
from pose.detector import PoseDetector
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
    overlay = OverlayRenderer()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            results = detector.process(frame)
            squat_state = analyzer.classify(results)
            overlay.draw(frame, results, squat_state)

            cv2.imshow("GymGuardian", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
    finally:
        detector.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
