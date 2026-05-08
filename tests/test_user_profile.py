"""Automated tests for calibration and local settings helpers."""

from __future__ import annotations

import pytest

import core.user_profile as user_profile
from core.user_profile import AppSettings, build_calibration_profile, load_app_settings, save_app_settings


def test_build_calibration_profile_creates_ordered_adaptive_thresholds() -> None:
    samples = ([170.0, 172.0, 168.0] * 12) + ([82.0, 84.0, 86.0] * 12)

    profile = build_calibration_profile(samples)
    config = profile.to_squat_config()

    assert profile.sample_count == len(samples)
    assert profile.lowest_knee_angle < profile.standing_knee_angle
    assert profile.lowest_knee_angle < config.down_knee_angle
    assert config.down_knee_angle < config.shallow_knee_angle
    assert config.shallow_knee_angle < config.rep_bottom_knee_angle
    assert config.rep_bottom_knee_angle < config.up_knee_angle
    assert config.up_knee_angle < profile.standing_knee_angle


def test_build_calibration_profile_rejects_insufficient_or_tiny_movement_samples() -> None:
    with pytest.raises(ValueError, match="Not enough"):
        build_calibration_profile([170.0] * 5)

    with pytest.raises(ValueError, match="Movement range"):
        build_calibration_profile([160.0, 162.0, 161.0] * 12)


def test_app_settings_persist_and_normalize_values(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(user_profile, "PROFILE_DIR", tmp_path)
    monkeypatch.setattr(user_profile, "SETTINGS_FILE", tmp_path / "settings.json")

    saved = save_app_settings(
        AppSettings(theme="neon", hide_incomplete_sessions=True, camera_index=99)
    )
    loaded = load_app_settings()

    assert saved.theme == "light"
    assert saved.hide_incomplete_sessions is True
    assert saved.camera_index == 0
    assert loaded == saved
