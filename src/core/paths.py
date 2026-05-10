"""Filesystem paths for GymGuardian."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SESSIONS_DIR = PROJECT_ROOT / "sessions"
INPUT_VIDEOS_DIR = PROJECT_ROOT / "input_videos"

ASSETS_DIR = PROJECT_ROOT / "assets"
MODELS_DIR = ASSETS_DIR / "models"
POSE_TASK_FILE = MODELS_DIR / "pose_landmarker_full.task"
