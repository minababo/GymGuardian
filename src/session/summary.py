"""Session summary placeholder for MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RepEvent:
    timestamp: float
    label: str
    reason: str = ""


@dataclass
class SessionSummary:
    started_at: datetime
    rep_count: int = 0
    bad_rep_count: int = 0
    events: List[RepEvent] = field(default_factory=list)
    knee_angles: List[float] = field(default_factory=list)
    issue_counts: Dict[str, int] = field(default_factory=dict)

    def add_event(self, timestamp: float, label: str, reason: str = "") -> None:
        self.events.append(RepEvent(timestamp=timestamp, label=label, reason=reason))

    def add_knee_angle(self, angle: float) -> None:
        self.knee_angles.append(angle)

    def record_issue(self, reason: str) -> None:
        for issue in self._split_issues(reason):
            self.issue_counts[issue] = self.issue_counts.get(issue, 0) + 1

    def record_rep_start(self, timestamp: float) -> None:
        self.add_event(timestamp=timestamp, label="rep_start")

    def record_rep_complete(self, timestamp: float, reason: str = "") -> None:
        self.add_event(timestamp=timestamp, label="rep_complete", reason=reason)

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "rep_count": self.rep_count,
            "bad_rep_count": self.bad_rep_count,
            "avg_knee_angle": self._average_knee_angle(),
            "min_knee_angle": self._minimum_knee_angle(),
            "issue_counts": dict(sorted(self.issue_counts.items())),
            "most_common_issue": self._most_common_issue(),
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
        output_path = output_dir / "summary.json"
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=2)
        return output_path

    def _average_knee_angle(self) -> Optional[float]:
        if not self.knee_angles:
            return None
        return round(sum(self.knee_angles) / len(self.knee_angles), 2)

    def _minimum_knee_angle(self) -> Optional[float]:
        if not self.knee_angles:
            return None
        return round(min(self.knee_angles), 2)

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
