"""Session summary placeholder for MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


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

    def add_event(self, timestamp: float, label: str, reason: str = "") -> None:
        self.events.append(RepEvent(timestamp=timestamp, label=label, reason=reason))

    def record_rep_start(self, timestamp: float) -> None:
        self.add_event(timestamp=timestamp, label="rep_start")

    def record_rep_complete(self, timestamp: float, reason: str = "") -> None:
        self.add_event(timestamp=timestamp, label="rep_complete", reason=reason)

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "rep_count": self.rep_count,
            "bad_rep_count": self.bad_rep_count,
            "events": [
                {
                    "timestamp": event.timestamp,
                    "label": event.label,
                    "reason": event.reason,
                }
                for event in self.events
            ],
        }
