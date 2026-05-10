"""MediaPipe Tasks pose detector wrapper (Pose Landmarker)."""

from __future__ import annotations

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

from core.paths import POSE_TASK_FILE


class PoseDetector:
    """Pose detector based on MediaPipe Tasks (Pose Landmarker)."""

    def __init__(self) -> None:
        if not POSE_TASK_FILE.exists():
            raise FileNotFoundError(
                f"Pose model not found at: {POSE_TASK_FILE}\n"
                "Place pose_landmarker_full.task in that location."
            )

        base_options = mp_tasks.BaseOptions(model_asset_path=str(POSE_TASK_FILE))
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._timestamp_ms = 0  # must increase for VIDEO mode

    def process(self, frame_bgr, timestamp_ms: int | None = None):
        """Run pose detection on a BGR frame and return a PoseLandmarkerResult."""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # ✅ In this MediaPipe build, Image is at top-level mediapipe.Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # VIDEO mode requires monotonically increasing timestamps.
        if timestamp_ms is None:
            self._timestamp_ms += 33  # ~30fps fallback for live webcam frames.
        else:
            self._timestamp_ms = max(int(timestamp_ms), self._timestamp_ms + 1)
        return self._landmarker.detect_for_video(mp_image, self._timestamp_ms)

    def close(self) -> None:
        self._landmarker.close()
