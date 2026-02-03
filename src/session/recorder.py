"""Session video recorder for GymGuardian."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2


class SessionRecorder:
    """Record webcam session frames to an MP4 file."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_path = output_dir / "session.mp4"
        self._writer: Optional[cv2.VideoWriter] = None
        self.enabled = False

    def start(self, frame_size: tuple[int, int], fps: float) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        safe_fps = fps if fps and fps > 1 else 30.0
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
        if self.enabled and self._writer is not None:
            self._writer.write(frame)

    def stop(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None
        self.enabled = False
