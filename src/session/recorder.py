"""Session video recorder for GymGuardian."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Optional

import cv2


class SessionRecorder:
    """Record webcam session frames to an MP4 file."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_path = output_dir / "session.mp4"
        self._writer: Optional[cv2.VideoWriter] = None
        self._fps = 30.0
        self._started_at: float | None = None
        self._written_frames = 0
        self.enabled = False

    def start(self, frame_size: tuple[int, int], fps: float) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        safe_fps = float(fps) if fps and 5 <= fps <= 60 else 30.0
        self._fps = float(safe_fps)
        self._started_at = None
        self._written_frames = 0
        writer = cv2.VideoWriter(
            str(self.output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            safe_fps,
            frame_size,
        )
        if not writer.isOpened():
            self.enabled = False
            print("Warning: failed to initialize session video writer. Continuing without recording.")
            return

        self._writer = writer
        self.enabled = True

    def write(self, frame) -> None:
        if not self.enabled or self._writer is None:
            return

        now = time.monotonic()
        if self._started_at is None:
            self._started_at = now

        elapsed = max(0.0, now - self._started_at)
        expected_frames = max(1, int(elapsed * self._fps) + 1)
        while self._written_frames < expected_frames:
            self._writer.write(frame)
            self._written_frames += 1

    def stop(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None
        self._started_at = None
        self._written_frames = 0
        self.enabled = False
