"""Session recording placeholder for MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2


@dataclass
class SessionRecorder:
    """Minimal recorder stub for later session video capture."""

    output_dir: Path
    fps: float
    frame_size: tuple[int, int]

    _writer: Optional[cv2.VideoWriter] = None

    def start(self, filename: str) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / filename
        self._writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.fps,
            self.frame_size,
        )

    def write(self, frame) -> None:
        if self._writer:
            self._writer.write(frame)

    def stop(self) -> None:
        if self._writer:
            self._writer.release()
            self._writer = None
