"""Filesystem paths for GymGuardian."""

from __future__ import annotations

from pathlib import Path
import sys

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    RESOURCE_ROOT = PROJECT_ROOT

SESSIONS_DIR = PROJECT_ROOT / "sessions"
INPUT_VIDEOS_DIR = PROJECT_ROOT / "input_videos"

ASSETS_DIR = RESOURCE_ROOT / "assets"
MODELS_DIR = ASSETS_DIR / "models"
POSE_TASK_FILE = MODELS_DIR / "pose_landmarker_full.task"
