"""Automated tests for the manual-label evaluation export harness."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import session.evaluation_export as evaluation_export
from session.evaluation_export import (
    aggregate_results,
    evaluate_label,
    export_evaluation_report,
    load_manual_labels,
)


LABEL_COLUMNS = [
    "case_id",
    "scenario",
    "session_folder",
    "manual_rep_count",
    "manual_bad_rep_count",
    "expected_issue",
    "manual_bad_sequence",
    "lighting",
    "camera_angle",
    "notes",
]


def _write_labels(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=LABEL_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_session(sessions_dir: Path, folder_name: str, summary: dict, sequence: list[int] | None = None) -> None:
    folder = sessions_dir / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    if sequence is not None:
        with (folder / "rep_metrics.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["rep_index", "timestamp_seconds", "is_bad", "issues"])
            for index, is_bad in enumerate(sequence, start=1):
                writer.writerow([index, f"{index:.2f}", is_bad, "too_shallow" if is_bad else ""])


def test_evaluation_export_scores_labelled_valid_session(tmp_path, monkeypatch) -> None:
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setattr(evaluation_export, "SESSIONS_DIR", sessions_dir)
    _write_session(
        sessions_dir,
        "20260509_120000",
        {
            "valid_session": True,
            "rep_count": 4,
            "bad_rep_count": 2,
            "issue_counts": {"too_shallow": 2},
            "most_common_issue": "too_shallow",
            "avg_fps": 18.5,
        },
        sequence=[0, 1, 0, 1],
    )
    labels_path = tmp_path / "manual_labels.csv"
    _write_labels(
        labels_path,
        [
            {
                "case_id": "AUTO-01",
                "scenario": "mixed squats",
                "session_folder": "20260509_120000",
                "manual_rep_count": 4,
                "manual_bad_rep_count": 2,
                "expected_issue": "too_shallow",
                "manual_bad_sequence": "0,1,0,1",
                "lighting": "indoor",
                "camera_angle": "front-facing",
                "notes": "automated smoke row",
            }
        ],
    )

    results_csv, report_html = export_evaluation_report(
        labels_path=labels_path,
        results_csv_path=tmp_path / "evaluation_results.csv",
        report_html_path=tmp_path / "evaluation_report.html",
    )

    assert results_csv.exists()
    assert report_html.exists()
    labels = load_manual_labels(labels_path)
    result = evaluate_label(labels[0])
    assert result.status == "evaluated"
    assert result.rep_accuracy_percent == 100.0
    assert result.bad_rate_difference == 0.0
    assert result.issue_match == "match"
    assert result.sequence_precision == 100.0
    assert result.sequence_recall == 100.0


def test_evaluation_handles_missing_session_and_incomplete_session(tmp_path, monkeypatch) -> None:
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setattr(evaluation_export, "SESSIONS_DIR", sessions_dir)
    _write_session(
        sessions_dir,
        "20260509_000000",
        {"valid_session": False, "rep_count": 0, "bad_rep_count": 0, "avg_fps": 12.0},
    )

    labels_path = tmp_path / "manual_labels.csv"
    _write_labels(
        labels_path,
        [
            {
                "case_id": "MISS-01",
                "scenario": "missing folder",
                "session_folder": "missing_folder",
                "manual_rep_count": 0,
                "manual_bad_rep_count": 0,
                "expected_issue": "none",
                "manual_bad_sequence": "",
                "lighting": "indoor",
                "camera_angle": "front-facing",
                "notes": "",
            },
            {
                "case_id": "INC-01",
                "scenario": "empty session",
                "session_folder": "20260509_000000",
                "manual_rep_count": 0,
                "manual_bad_rep_count": 0,
                "expected_issue": "none",
                "manual_bad_sequence": "",
                "lighting": "indoor",
                "camera_angle": "front-facing",
                "notes": "",
            },
        ],
    )

    labels = load_manual_labels(labels_path)
    results = [evaluate_label(label) for label in labels]

    assert results[0].status == "missing_session"
    assert results[1].status == "incomplete_session"
    aggregate = aggregate_results(results)
    assert aggregate.evaluated_rows == 0
    assert aggregate.skipped_rows == 2
