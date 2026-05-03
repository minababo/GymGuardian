"""Local user calibration storage for adaptive squat thresholds."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
import json
from pathlib import Path

from core.config import CALIBRATION_CONFIG, SQUAT_CONFIG, SquatConfig
from core.paths import PROJECT_ROOT


PROFILE_DIR = PROJECT_ROOT / "user_data"
CALIBRATION_FILE = PROFILE_DIR / "calibration.json"


@dataclass(frozen=True)
class CalibrationProfile:
    created_at: str
    sample_count: int
    standing_knee_angle: float
    lowest_knee_angle: float
    calibrated_down_angle: float
    calibrated_shallow_angle: float
    calibrated_rep_bottom_angle: float
    calibrated_up_angle: float

    def to_squat_config(self) -> SquatConfig:
        return replace(
            SQUAT_CONFIG,
            down_knee_angle=self.calibrated_down_angle,
            shallow_knee_angle=self.calibrated_shallow_angle,
            rep_bottom_knee_angle=self.calibrated_rep_bottom_angle,
            up_knee_angle=self.calibrated_up_angle,
        )


def load_calibration_profile() -> CalibrationProfile | None:
    if not CALIBRATION_FILE.exists():
        return None

    try:
        data = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
        return CalibrationProfile(
            created_at=str(data["created_at"]),
            sample_count=int(data["sample_count"]),
            standing_knee_angle=float(data["standing_knee_angle"]),
            lowest_knee_angle=float(data["lowest_knee_angle"]),
            calibrated_down_angle=float(data["calibrated_down_angle"]),
            calibrated_shallow_angle=float(data["calibrated_shallow_angle"]),
            calibrated_rep_bottom_angle=float(data["calibrated_rep_bottom_angle"]),
            calibrated_up_angle=float(data["calibrated_up_angle"]),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def save_calibration_profile(profile: CalibrationProfile) -> Path:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    CALIBRATION_FILE.write_text(
        json.dumps(asdict(profile), indent=2),
        encoding="utf-8",
    )
    return CALIBRATION_FILE


def reset_calibration_profile() -> None:
    try:
        CALIBRATION_FILE.unlink()
    except FileNotFoundError:
        return


def load_squat_config() -> SquatConfig:
    profile = load_calibration_profile()
    if profile is None:
        return SQUAT_CONFIG
    return profile.to_squat_config()


def build_calibration_profile(knee_angles: list[float]) -> CalibrationProfile:
    valid_angles = [angle for angle in knee_angles if 30.0 <= angle <= 180.0]
    if len(valid_angles) < CALIBRATION_CONFIG.min_samples:
        raise ValueError("Not enough valid knee-angle samples.")

    sorted_angles = sorted(valid_angles)
    bucket_size = max(3, len(sorted_angles) // 5)
    lowest_knee_angle = _mean(sorted_angles[:bucket_size])
    standing_knee_angle = _mean(sorted_angles[-bucket_size:])
    movement_range = standing_knee_angle - lowest_knee_angle

    if movement_range < CALIBRATION_CONFIG.min_movement_range:
        raise ValueError("Movement range too small for reliable calibration.")

    down_margin = _clamp(
        movement_range * CALIBRATION_CONFIG.down_margin_ratio,
        CALIBRATION_CONFIG.min_down_margin,
        CALIBRATION_CONFIG.max_down_margin,
    )
    shallow_margin = _clamp(
        movement_range * CALIBRATION_CONFIG.shallow_margin_ratio,
        CALIBRATION_CONFIG.min_shallow_margin,
        CALIBRATION_CONFIG.max_shallow_margin,
    )
    rep_bottom_margin = _clamp(
        movement_range * CALIBRATION_CONFIG.rep_bottom_margin_ratio,
        CALIBRATION_CONFIG.min_rep_bottom_margin,
        CALIBRATION_CONFIG.max_rep_bottom_margin,
    )
    up_margin = _clamp(
        movement_range * CALIBRATION_CONFIG.up_margin_ratio,
        CALIBRATION_CONFIG.min_up_margin,
        CALIBRATION_CONFIG.max_up_margin,
    )

    calibrated_up_angle = standing_knee_angle - up_margin
    calibrated_down_angle = min(
        lowest_knee_angle + down_margin,
        calibrated_up_angle - 35.0,
    )
    calibrated_shallow_angle = min(
        max(calibrated_down_angle + 5.0, lowest_knee_angle + shallow_margin),
        calibrated_up_angle - 20.0,
    )
    calibrated_rep_bottom_angle = min(
        max(calibrated_shallow_angle + 10.0, lowest_knee_angle + rep_bottom_margin),
        calibrated_up_angle - 8.0,
    )

    return CalibrationProfile(
        created_at=datetime.now().isoformat(timespec="seconds"),
        sample_count=len(valid_angles),
        standing_knee_angle=round(standing_knee_angle, 1),
        lowest_knee_angle=round(lowest_knee_angle, 1),
        calibrated_down_angle=round(calibrated_down_angle, 1),
        calibrated_shallow_angle=round(calibrated_shallow_angle, 1),
        calibrated_rep_bottom_angle=round(calibrated_rep_bottom_angle, 1),
        calibrated_up_angle=round(calibrated_up_angle, 1),
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
