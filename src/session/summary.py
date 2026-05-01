"""Session summary helpers for squat-session analytics and evidence export."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from session.insights import bad_rep_percentage, build_recommendation


@dataclass
class RepEvent:
    timestamp: float
    label: str
    reason: str = ""


@dataclass
class CompletedRep:
    rep_index: int
    timestamp: float
    is_bad: bool
    issues: List[str] = field(default_factory=list)
    min_knee_angle: Optional[float] = None
    min_ankle_angle: Optional[float] = None
    max_torso_angle: Optional[float] = None


@dataclass
class SessionSummary:
    started_at: datetime
    rep_count: int = 0
    bad_rep_count: int = 0
    events: List[RepEvent] = field(default_factory=list)
    completed_reps: List[CompletedRep] = field(default_factory=list)
    knee_angles: List[float] = field(default_factory=list)
    ankle_angles: List[float] = field(default_factory=list)
    torso_angles: List[float] = field(default_factory=list)
    fps_samples: List[float] = field(default_factory=list)
    issue_counts: Dict[str, int] = field(default_factory=dict)

    def add_event(self, timestamp: float, label: str, reason: str = "") -> None:
        self.events.append(RepEvent(timestamp=timestamp, label=label, reason=reason))

    def add_pose_metrics(
        self,
        *,
        knee_angle: Optional[float] = None,
        ankle_angle: Optional[float] = None,
        torso_angle: Optional[float] = None,
    ) -> None:
        if knee_angle is not None:
            self.knee_angles.append(knee_angle)
        if ankle_angle is not None:
            self.ankle_angles.append(ankle_angle)
        if torso_angle is not None:
            self.torso_angles.append(torso_angle)

    def add_fps_sample(self, fps: float) -> None:
        if fps > 0:
            self.fps_samples.append(fps)

    def record_issues(self, issues: Sequence[str]) -> None:
        for issue in issues:
            issue_name = issue.strip()
            if not issue_name:
                continue
            self.issue_counts[issue_name] = self.issue_counts.get(issue_name, 0) + 1

    def record_issue(self, reason: str) -> None:
        self.record_issues(self._split_issues(reason))

    def record_rep_start(self, timestamp: float) -> None:
        self.add_event(timestamp=timestamp, label="rep_start")

    def record_rep_complete(self, timestamp: float, reason: str = "") -> None:
        self.add_event(timestamp=timestamp, label="rep_complete", reason=reason)

    def record_completed_rep(
        self,
        *,
        rep_index: int,
        timestamp: float,
        is_bad: bool,
        issues: Sequence[str],
        min_knee_angle: Optional[float],
        min_ankle_angle: Optional[float],
        max_torso_angle: Optional[float],
    ) -> None:
        self.completed_reps.append(
            CompletedRep(
                rep_index=rep_index,
                timestamp=timestamp,
                is_bad=is_bad,
                issues=list(issues),
                min_knee_angle=self._round_optional(min_knee_angle),
                min_ankle_angle=self._round_optional(min_ankle_angle),
                max_torso_angle=self._round_optional(max_torso_angle),
            )
        )

    def to_dict(self) -> dict:
        valid_session = self.rep_count > 0
        return {
            "started_at": self.started_at.isoformat(),
            "valid_session": valid_session,
            "rep_count": self.rep_count,
            "bad_rep_count": self.bad_rep_count,
            "avg_fps": self._average_value(self.fps_samples),
            "min_fps": self._minimum_value(self.fps_samples),
            "max_fps": self._maximum_value(self.fps_samples),
            "avg_knee_angle": self._average_value(self.knee_angles),
            "min_knee_angle": self._minimum_value(self.knee_angles),
            "avg_ankle_angle": self._average_value(self.ankle_angles),
            "min_ankle_angle": self._minimum_value(self.ankle_angles),
            "avg_torso_angle": self._average_value(self.torso_angles),
            "max_torso_angle": self._maximum_value(self.torso_angles),
            "issue_counts": dict(sorted(self.issue_counts.items())),
            "most_common_issue": self._most_common_issue(),
            "completed_reps": [
                {
                    "rep_index": rep.rep_index,
                    "timestamp": rep.timestamp,
                    "is_bad": rep.is_bad,
                    "issues": list(rep.issues),
                    "min_knee_angle": rep.min_knee_angle,
                    "min_ankle_angle": rep.min_ankle_angle,
                    "max_torso_angle": rep.max_torso_angle,
                }
                for rep in self.completed_reps
            ],
            "events": [
                {
                    "timestamp": event.timestamp,
                    "label": event.label,
                    "reason": event.reason,
                }
                for event in self.events
            ],
        }

    def save(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        summary_data = self.to_dict()
        summary_path = output_dir / "summary.json"
        with summary_path.open("w", encoding="utf-8") as file:
            json.dump(summary_data, file, indent=2)

        self._save_rep_metrics_csv(output_dir / "rep_metrics.csv")
        self._save_session_report(output_dir / "session_report.txt", summary_data)
        return summary_path

    def _save_rep_metrics_csv(self, output_path: Path) -> None:
        with output_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "rep_index",
                    "timestamp_seconds",
                    "is_bad",
                    "issues",
                    "min_knee_angle",
                    "min_ankle_angle",
                    "max_torso_angle",
                ]
            )
            for rep in self.completed_reps:
                writer.writerow(
                    [
                        rep.rep_index,
                        f"{rep.timestamp:.2f}",
                        int(rep.is_bad),
                        ", ".join(rep.issues),
                        self._format_optional(rep.min_knee_angle),
                        self._format_optional(rep.min_ankle_angle),
                        self._format_optional(rep.max_torso_angle),
                    ]
                )

    def _save_session_report(self, output_path: Path, summary_data: dict) -> None:
        main_concern, suggested_improvement, focus_area = build_recommendation(
            summary_data.get("most_common_issue")
        )
        valid_session = bool(summary_data.get("valid_session"))
        lines = [
            "GymGuardian Session Report",
            f"Started at: {summary_data.get('started_at', 'N/A')}",
            f"Session status: {'valid' if valid_session else 'incomplete'}",
            f"Total reps: {summary_data.get('rep_count', 0)}",
            f"Bad reps: {summary_data.get('bad_rep_count', 0)}",
            (
                "Bad rep rate: "
                f"{bad_rep_percentage(self.rep_count, self.bad_rep_count):.2f}%"
            ),
            f"Average FPS: {self._display_metric(summary_data.get('avg_fps'))}",
            f"Minimum FPS: {self._display_metric(summary_data.get('min_fps'))}",
            f"Maximum FPS: {self._display_metric(summary_data.get('max_fps'))}",
            f"Average knee angle: {self._display_metric(summary_data.get('avg_knee_angle'))}",
            f"Minimum knee angle: {self._display_metric(summary_data.get('min_knee_angle'))}",
            f"Average ankle angle: {self._display_metric(summary_data.get('avg_ankle_angle'))}",
            f"Minimum ankle angle: {self._display_metric(summary_data.get('min_ankle_angle'))}",
            f"Average torso angle: {self._display_metric(summary_data.get('avg_torso_angle'))}",
            f"Maximum torso angle: {self._display_metric(summary_data.get('max_torso_angle'))}",
            f"Most common issue: {summary_data.get('most_common_issue') or 'none'}",
            f"Main concern: {main_concern}",
            f"Suggested improvement: {suggested_improvement}",
            f"Focus area: {focus_area}",
        ]
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _most_common_issue(self) -> Optional[str]:
        if not self.issue_counts:
            return None
        sorted_issues = sorted(
            self.issue_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
        return sorted_issues[0][0]

    @staticmethod
    def _split_issues(reason: str) -> List[str]:
        return [issue.strip() for issue in reason.split(",") if issue.strip()]

    @staticmethod
    def _average_value(values: List[float]) -> Optional[float]:
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    @staticmethod
    def _minimum_value(values: List[float]) -> Optional[float]:
        if not values:
            return None
        return round(min(values), 2)

    @staticmethod
    def _maximum_value(values: List[float]) -> Optional[float]:
        if not values:
            return None
        return round(max(values), 2)

    @staticmethod
    def _round_optional(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        return round(value, 2)

    @staticmethod
    def _format_optional(value: Optional[float]) -> str:
        if value is None:
            return ""
        return f"{value:.2f}"

    @staticmethod
    def _display_metric(value: Optional[float]) -> str:
        if value is None:
            return "N/A"
        return f"{value:.2f}"
