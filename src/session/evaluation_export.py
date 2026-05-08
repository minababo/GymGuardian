"""Evaluation export helpers for manually labelled GymGuardian sessions."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Iterable, Optional

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.paths import PROJECT_ROOT, SESSIONS_DIR  # noqa: E402


EVALUATION_DIR = PROJECT_ROOT / "docs" / "evaluation"
DEFAULT_LABELS_FILE = EVALUATION_DIR / "manual_labels.csv"
EXPORTS_DIR = PROJECT_ROOT / "exports"
DEFAULT_RESULTS_CSV = EXPORTS_DIR / "evaluation_results.csv"
DEFAULT_REPORT_HTML = EXPORTS_DIR / "evaluation_report.html"

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

RESULT_COLUMNS = [
    "case_id",
    "scenario",
    "session_folder",
    "status",
    "manual_rep_count",
    "detected_rep_count",
    "rep_count_error",
    "absolute_rep_error",
    "rep_accuracy_percent",
    "manual_bad_rep_count",
    "detected_bad_rep_count",
    "bad_rep_count_error",
    "manual_bad_rate",
    "detected_bad_rate",
    "bad_rate_difference",
    "expected_issue",
    "detected_issue",
    "issue_match",
    "sequence_precision",
    "sequence_recall",
    "avg_fps",
    "lighting",
    "camera_angle",
    "notes",
    "message",
]


@dataclass(frozen=True)
class ManualLabel:
    case_id: str
    scenario: str
    session_folder: str
    manual_rep_count: Optional[int]
    manual_bad_rep_count: Optional[int]
    expected_issue: str
    manual_bad_sequence: tuple[bool, ...] | None
    lighting: str
    camera_angle: str
    notes: str
    message: str = ""


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    scenario: str
    session_folder: str
    status: str
    manual_rep_count: Optional[int] = None
    detected_rep_count: Optional[int] = None
    rep_count_error: Optional[int] = None
    absolute_rep_error: Optional[int] = None
    rep_accuracy_percent: Optional[float] = None
    manual_bad_rep_count: Optional[int] = None
    detected_bad_rep_count: Optional[int] = None
    bad_rep_count_error: Optional[int] = None
    manual_bad_rate: Optional[float] = None
    detected_bad_rate: Optional[float] = None
    bad_rate_difference: Optional[float] = None
    expected_issue: str = ""
    detected_issue: Optional[str] = None
    issue_match: str = "N/A"
    sequence_precision: Optional[float] = None
    sequence_recall: Optional[float] = None
    sequence_tp: int = 0
    sequence_fp: int = 0
    sequence_fn: int = 0
    avg_fps: Optional[float] = None
    lighting: str = ""
    camera_angle: str = ""
    notes: str = ""
    message: str = ""


@dataclass(frozen=True)
class EvaluationAggregate:
    total_rows: int
    evaluated_rows: int
    skipped_rows: int
    total_manual_reps: int
    total_detected_reps: int
    total_manual_bad_reps: int
    total_detected_bad_reps: int
    rep_accuracy_overall: Optional[float]
    rep_accuracy_average: Optional[float]
    bad_count_accuracy_overall: Optional[float]
    issue_match_rate: Optional[float]
    sequence_precision: Optional[float]
    sequence_recall: Optional[float]
    avg_fps: Optional[float]


def export_evaluation_report(
    labels_path: Path = DEFAULT_LABELS_FILE,
    results_csv_path: Path = DEFAULT_RESULTS_CSV,
    report_html_path: Path = DEFAULT_REPORT_HTML,
) -> tuple[Path, Path]:
    """Evaluate labelled session outputs and write CSV plus HTML reports."""
    if not labels_path.exists():
        create_label_template(labels_path)
        print(f"Created manual label template: {labels_path}")
        print("Add labelled session rows, then rerun this command.")

    labels = load_manual_labels(labels_path)
    results = [evaluate_label(label) for label in labels]
    aggregate = aggregate_results(results)

    results_csv_path.parent.mkdir(parents=True, exist_ok=True)
    report_html_path.parent.mkdir(parents=True, exist_ok=True)
    write_results_csv(results, results_csv_path)
    report_html_path.write_text(
        build_html_report(results, aggregate, labels_path),
        encoding="utf-8",
    )
    return results_csv_path, report_html_path


def create_label_template(labels_path: Path = DEFAULT_LABELS_FILE) -> Path:
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    with labels_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(LABEL_COLUMNS)
    return labels_path


def load_manual_labels(labels_path: Path = DEFAULT_LABELS_FILE) -> list[ManualLabel]:
    if not labels_path.exists():
        return []

    labels: list[ManualLabel] = []
    with labels_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row_number, row in enumerate(reader, start=2):
            if _is_blank_row(row):
                continue
            labels.append(_parse_label(row, row_number))
    return labels


def evaluate_label(label: ManualLabel) -> EvaluationResult:
    base = {
        "case_id": label.case_id,
        "scenario": label.scenario,
        "session_folder": label.session_folder,
        "manual_rep_count": label.manual_rep_count,
        "manual_bad_rep_count": label.manual_bad_rep_count,
        "expected_issue": label.expected_issue,
        "lighting": label.lighting,
        "camera_angle": label.camera_angle,
        "notes": label.notes,
    }

    if not label.session_folder:
        return EvaluationResult(**base, status="unlabelled", message="Missing session_folder.")
    if label.manual_rep_count is None or label.manual_bad_rep_count is None:
        return EvaluationResult(
            **base,
            status="unlabelled",
            message=label.message or "Manual rep and bad-rep counts are required.",
        )
    if label.manual_rep_count < 0 or label.manual_bad_rep_count < 0:
        return EvaluationResult(**base, status="invalid_label", message="Manual counts cannot be negative.")
    if label.manual_bad_rep_count > label.manual_rep_count:
        return EvaluationResult(
            **base,
            status="invalid_label",
            message="manual_bad_rep_count cannot exceed manual_rep_count.",
        )

    session_dir = SESSIONS_DIR / label.session_folder
    if not session_dir.exists():
        return EvaluationResult(**base, status="missing_session", message="Session folder was not found.")

    summary_path = session_dir / "summary.json"
    if not summary_path.exists():
        return EvaluationResult(**base, status="missing_summary", message="summary.json was not found.")

    try:
        summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return EvaluationResult(**base, status="invalid_summary", message=f"Could not read summary.json: {exc}")

    detected_rep_count = _safe_int(summary_data.get("rep_count")) or 0
    detected_bad_rep_count = _safe_int(summary_data.get("bad_rep_count")) or 0
    detected_issue = _normalize_issue(summary_data.get("most_common_issue"))
    issue_counts = _safe_issue_counts(summary_data.get("issue_counts"))
    avg_fps = _safe_float(summary_data.get("avg_fps"))
    valid_session = bool(summary_data.get("valid_session")) and detected_rep_count > 0

    if not valid_session:
        return EvaluationResult(
            **base,
            status="incomplete_session",
            detected_rep_count=detected_rep_count,
            detected_bad_rep_count=detected_bad_rep_count,
            detected_issue=detected_issue,
            avg_fps=avg_fps,
            message="Incomplete sessions are excluded from meaningful evaluation.",
        )

    manual_bad_rate = _bad_rate(label.manual_rep_count, label.manual_bad_rep_count)
    detected_bad_rate = _bad_rate(detected_rep_count, detected_bad_rep_count)
    rep_count_error = detected_rep_count - label.manual_rep_count
    absolute_rep_error = abs(rep_count_error)
    bad_rep_count_error = detected_bad_rep_count - label.manual_bad_rep_count
    rep_accuracy = _count_accuracy(label.manual_rep_count, detected_rep_count)
    bad_rate_difference = _optional_difference(detected_bad_rate, manual_bad_rate)
    issue_match = _issue_match(label.expected_issue, detected_issue, issue_counts)
    detected_sequence = _load_detected_bad_sequence(session_dir, summary_data)
    sequence_precision, sequence_recall, tp, fp, fn = _sequence_metrics(
        label.manual_bad_sequence,
        detected_sequence,
    )

    message_parts = [part for part in [label.message] if part]
    if label.manual_bad_sequence is None:
        message_parts.append("Per-rep sequence not labelled; count-level comparison only.")

    return EvaluationResult(
        **base,
        status="evaluated",
        detected_rep_count=detected_rep_count,
        rep_count_error=rep_count_error,
        absolute_rep_error=absolute_rep_error,
        rep_accuracy_percent=rep_accuracy,
        detected_bad_rep_count=detected_bad_rep_count,
        bad_rep_count_error=bad_rep_count_error,
        manual_bad_rate=manual_bad_rate,
        detected_bad_rate=detected_bad_rate,
        bad_rate_difference=bad_rate_difference,
        detected_issue=detected_issue,
        issue_match=issue_match,
        sequence_precision=sequence_precision,
        sequence_recall=sequence_recall,
        sequence_tp=tp,
        sequence_fp=fp,
        sequence_fn=fn,
        avg_fps=avg_fps,
        message=" ".join(message_parts),
    )


def aggregate_results(results: Iterable[EvaluationResult]) -> EvaluationAggregate:
    rows = list(results)
    evaluated = [row for row in rows if row.status == "evaluated"]
    total_manual_reps = sum(row.manual_rep_count or 0 for row in evaluated)
    total_detected_reps = sum(row.detected_rep_count or 0 for row in evaluated)
    total_manual_bad = sum(row.manual_bad_rep_count or 0 for row in evaluated)
    total_detected_bad = sum(row.detected_bad_rep_count or 0 for row in evaluated)
    total_abs_rep_error = sum(row.absolute_rep_error or 0 for row in evaluated)
    total_abs_bad_error = sum(abs(row.bad_rep_count_error or 0) for row in evaluated)

    issue_rows = [row for row in evaluated if row.issue_match in ("match", "mismatch")]
    issue_matches = sum(1 for row in issue_rows if row.issue_match == "match")
    sequence_tp = sum(row.sequence_tp for row in evaluated)
    sequence_fp = sum(row.sequence_fp for row in evaluated)
    sequence_fn = sum(row.sequence_fn for row in evaluated)

    return EvaluationAggregate(
        total_rows=len(rows),
        evaluated_rows=len(evaluated),
        skipped_rows=len(rows) - len(evaluated),
        total_manual_reps=total_manual_reps,
        total_detected_reps=total_detected_reps,
        total_manual_bad_reps=total_manual_bad,
        total_detected_bad_reps=total_detected_bad,
        rep_accuracy_overall=_accuracy_from_abs_error(total_manual_reps, total_detected_reps, total_abs_rep_error),
        rep_accuracy_average=_average_optional([row.rep_accuracy_percent for row in evaluated]),
        bad_count_accuracy_overall=_accuracy_from_abs_error(total_manual_bad, total_detected_bad, total_abs_bad_error),
        issue_match_rate=(100.0 * issue_matches / len(issue_rows)) if issue_rows else None,
        sequence_precision=_divide_percent(sequence_tp, sequence_tp + sequence_fp),
        sequence_recall=_divide_percent(sequence_tp, sequence_tp + sequence_fn),
        avg_fps=_average_optional([row.avg_fps for row in evaluated]),
    )


def write_results_csv(results: Iterable[EvaluationResult], output_path: Path = DEFAULT_RESULTS_CSV) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        for result in results:
            writer.writerow(_result_to_csv_row(result))
    return output_path


def build_html_report(
    results: list[EvaluationResult],
    aggregate: EvaluationAggregate,
    labels_path: Path = DEFAULT_LABELS_FILE,
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GymGuardian Evaluation Report</title>
  <style>
    :root {{
      --bg: #eef5ef;
      --panel: #ffffff;
      --panel-soft: #f6faf6;
      --ink: #20332a;
      --muted: #64736a;
      --line: #bfd0c2;
      --green: #2f7d52;
      --green-soft: #dff1e4;
      --blue: #2f6f9f;
      --amber: #ad7624;
      --red: #b94d45;
      --shadow: 0 18px 45px rgba(35, 61, 42, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top right, rgba(70, 132, 84, 0.16), transparent 28rem),
        linear-gradient(135deg, #f8fbf8 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 40px 28px 56px; }}
    header {{ display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; margin-bottom: 26px; }}
    h1 {{ margin: 0 0 8px; font-size: 42px; letter-spacing: -0.04em; }}
    h2 {{ margin: 0 0 16px; font-size: 22px; letter-spacing: -0.02em; }}
    p {{ margin: 0; color: var(--muted); line-height: 1.55; }}
    .badge {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 8px 14px; background: var(--green-soft); color: var(--green); font-weight: 800; white-space: nowrap; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 24px 0; }}
    .card {{ background: rgba(255, 255, 255, 0.9); border: 1px solid var(--line); border-radius: 22px; padding: 22px; box-shadow: var(--shadow); }}
    .metric-label {{ color: var(--muted); font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; }}
    .metric-value {{ margin-top: 10px; font-size: 30px; font-weight: 850; letter-spacing: -0.03em; }}
    .section {{ margin-top: 18px; background: rgba(255, 255, 255, 0.9); border: 1px solid var(--line); border-radius: 24px; padding: 24px; box-shadow: var(--shadow); overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 12px 10px; border-bottom: 1px solid #d8e4da; font-size: 14px; vertical-align: top; }}
    th {{ color: var(--muted); background: var(--panel-soft); text-transform: uppercase; letter-spacing: 0.06em; font-size: 12px; white-space: nowrap; }}
    tr:last-child td {{ border-bottom: 0; }}
    .note {{ margin-top: 20px; padding: 16px 18px; border-left: 5px solid var(--green); background: #edf7ef; border-radius: 14px; }}
    .good {{ color: var(--green); font-weight: 800; }}
    .warn {{ color: var(--amber); font-weight: 800; }}
    .bad {{ color: var(--red); font-weight: 800; }}
    .muted {{ color: var(--muted); }}
    @media (max-width: 900px) {{ header {{ display: grid; }} .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>GymGuardian Evaluation Report</h1>
        <p>Manual video labels compared against saved GymGuardian session summaries.</p>
      </div>
      <div class="badge">Generated {escape(generated_at)}</div>
    </header>

    <section class="grid">
      {_metric_card("Labelled rows", aggregate.total_rows)}
      {_metric_card("Evaluated rows", aggregate.evaluated_rows)}
      {_metric_card("Overall rep accuracy", _format_percent(aggregate.rep_accuracy_overall), _score_class(aggregate.rep_accuracy_overall))}
      {_metric_card("Average rep accuracy", _format_percent(aggregate.rep_accuracy_average), _score_class(aggregate.rep_accuracy_average))}
      {_metric_card("Manual reps", aggregate.total_manual_reps)}
      {_metric_card("Detected reps", aggregate.total_detected_reps)}
      {_metric_card("Issue match rate", _format_percent(aggregate.issue_match_rate), _score_class(aggregate.issue_match_rate))}
      {_metric_card("Average FPS", _format_float(aggregate.avg_fps))}
    </section>

    <section class="section">
      <h2>Scenario Results</h2>
      {_results_table(results)}
      <div class="note">
        Labels file: <strong>{escape(str(labels_path))}</strong>. Incomplete sessions are flagged and excluded from aggregate meaningful-session evaluation.
      </div>
    </section>

    <section class="section">
      <h2>Bad-Rep Detection Summary</h2>
      <p>Manual bad-rep counts are compared with detected bad-rep counts for every evaluated row. Per-rep precision and recall are calculated only when <code>manual_bad_sequence</code> is supplied.</p>
      <div class="grid">
        {_metric_card("Manual bad reps", aggregate.total_manual_bad_reps)}
        {_metric_card("Detected bad reps", aggregate.total_detected_bad_reps)}
        {_metric_card("Bad-count accuracy", _format_percent(aggregate.bad_count_accuracy_overall), _score_class(aggregate.bad_count_accuracy_overall))}
        {_metric_card("Sequence precision", _format_percent(aggregate.sequence_precision), _score_class(aggregate.sequence_precision))}
        {_metric_card("Sequence recall", _format_percent(aggregate.sequence_recall), _score_class(aggregate.sequence_recall))}
      </div>
      <div class="note">
        This report evaluates GymGuardian as a complete system. It does not claim training accuracy for a custom machine-learning model, because the project uses MediaPipe pose estimation plus rule-based squat analysis.
      </div>
    </section>
  </main>
</body>
</html>
"""


def _parse_label(row: dict[str, str], row_number: int) -> ManualLabel:
    case_id = _clean(row.get("case_id")) or f"ROW-{row_number}"
    manual_rep_count, rep_message = _parse_optional_int(row.get("manual_rep_count"))
    manual_bad_count, bad_message = _parse_optional_int(row.get("manual_bad_rep_count"))
    manual_sequence, sequence_message = _parse_bad_sequence(row.get("manual_bad_sequence"))
    message = " ".join(part for part in [rep_message, bad_message, sequence_message] if part)
    return ManualLabel(
        case_id=case_id,
        scenario=_clean(row.get("scenario")),
        session_folder=_clean(row.get("session_folder")),
        manual_rep_count=manual_rep_count,
        manual_bad_rep_count=manual_bad_count,
        expected_issue=_clean(row.get("expected_issue")),
        manual_bad_sequence=manual_sequence,
        lighting=_clean(row.get("lighting")),
        camera_angle=_clean(row.get("camera_angle")),
        notes=_clean(row.get("notes")),
        message=message,
    )


def _load_detected_bad_sequence(session_dir: Path, summary_data: dict) -> tuple[bool, ...]:
    csv_path = session_dir / "rep_metrics.csv"
    if csv_path.exists():
        sequence: list[bool] = []
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    parsed = _parse_bool(row.get("is_bad"))
                    if parsed is not None:
                        sequence.append(parsed)
        except OSError:
            sequence = []
        if sequence:
            return tuple(sequence)

    completed_reps = summary_data.get("completed_reps")
    if isinstance(completed_reps, list):
        return tuple(bool(rep.get("is_bad")) for rep in completed_reps if isinstance(rep, dict))
    return tuple()


def _sequence_metrics(
    manual_sequence: tuple[bool, ...] | None,
    detected_sequence: tuple[bool, ...],
) -> tuple[Optional[float], Optional[float], int, int, int]:
    if manual_sequence is None:
        return None, None, 0, 0, 0

    tp = fp = fn = 0
    max_len = max(len(manual_sequence), len(detected_sequence))
    for index in range(max_len):
        manual_bad = manual_sequence[index] if index < len(manual_sequence) else False
        detected_bad = detected_sequence[index] if index < len(detected_sequence) else False
        if manual_bad and detected_bad:
            tp += 1
        elif not manual_bad and detected_bad:
            fp += 1
        elif manual_bad and not detected_bad:
            fn += 1

    return _divide_percent(tp, tp + fp), _divide_percent(tp, tp + fn), tp, fp, fn


def _issue_match(expected_issue: str, detected_issue: Optional[str], issue_counts: dict[str, int]) -> str:
    expected_issues, was_labelled = _parse_expected_issues(expected_issue)
    if not was_labelled:
        return "N/A"
    detected_issues = set(issue_counts.keys())
    if detected_issue:
        detected_issues.add(detected_issue)
    if not expected_issues:
        return "match" if not detected_issues else "mismatch"
    return "match" if expected_issues.intersection(detected_issues) else "mismatch"


def _parse_expected_issues(value: str) -> tuple[set[str], bool]:
    raw = _clean(value)
    if not raw:
        return set(), False
    parts = [_normalize_issue(part) for part in re.split(r"[,;|]", raw)]
    issues = {part for part in parts if part}
    return issues, True


def _safe_issue_counts(value) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for key, count in value.items():
        issue = _normalize_issue(key)
        safe_count = _safe_int(count)
        if issue and safe_count and safe_count > 0:
            counts[issue] = safe_count
    return counts


def _result_to_csv_row(result: EvaluationResult) -> dict[str, str]:
    return {
        "case_id": result.case_id,
        "scenario": result.scenario,
        "session_folder": result.session_folder,
        "status": result.status,
        "manual_rep_count": _format_optional_int(result.manual_rep_count),
        "detected_rep_count": _format_optional_int(result.detected_rep_count),
        "rep_count_error": _format_optional_int(result.rep_count_error),
        "absolute_rep_error": _format_optional_int(result.absolute_rep_error),
        "rep_accuracy_percent": _format_optional_float(result.rep_accuracy_percent),
        "manual_bad_rep_count": _format_optional_int(result.manual_bad_rep_count),
        "detected_bad_rep_count": _format_optional_int(result.detected_bad_rep_count),
        "bad_rep_count_error": _format_optional_int(result.bad_rep_count_error),
        "manual_bad_rate": _format_optional_float(result.manual_bad_rate),
        "detected_bad_rate": _format_optional_float(result.detected_bad_rate),
        "bad_rate_difference": _format_optional_float(result.bad_rate_difference),
        "expected_issue": result.expected_issue,
        "detected_issue": result.detected_issue or "none",
        "issue_match": result.issue_match,
        "sequence_precision": _format_optional_float(result.sequence_precision),
        "sequence_recall": _format_optional_float(result.sequence_recall),
        "avg_fps": _format_optional_float(result.avg_fps),
        "lighting": result.lighting,
        "camera_angle": result.camera_angle,
        "notes": result.notes,
        "message": result.message,
    }


def _results_table(results: list[EvaluationResult]) -> str:
    if not results:
        return "<p>No manual label rows found. Add labelled sessions to <code>manual_labels.csv</code>, then rerun the evaluator.</p>"

    rows = []
    for result in results:
        status_class = "good" if result.status == "evaluated" else "warn"
        issue_class = "good" if result.issue_match == "match" else "bad" if result.issue_match == "mismatch" else "muted"
        rows.append(
            "<tr>"
            f"<td>{escape(result.case_id)}</td>"
            f"<td>{escape(result.scenario or 'N/A')}</td>"
            f"<td>{escape(result.session_folder or 'N/A')}</td>"
            f"<td class=\"{status_class}\">{escape(result.status)}</td>"
            f"<td>{escape(_format_count_pair(result.manual_rep_count, result.detected_rep_count))}</td>"
            f"<td>{escape(_format_count_pair(result.manual_bad_rep_count, result.detected_bad_rep_count))}</td>"
            f"<td>{escape(_format_percent(result.rep_accuracy_percent))}</td>"
            f"<td>{escape(_format_signed_float(result.bad_rate_difference, ' pts'))}</td>"
            f"<td>{escape(result.expected_issue or 'N/A')}</td>"
            f"<td>{escape(result.detected_issue or 'none')}</td>"
            f"<td class=\"{issue_class}\">{escape(result.issue_match)}</td>"
            f"<td>{escape(_format_float(result.avg_fps))}</td>"
            f"<td>{escape(result.message)}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr>"
        "<th>Case</th><th>Scenario</th><th>Session</th><th>Status</th>"
        "<th>Reps M/D</th><th>Bad M/D</th><th>Rep accuracy</th><th>Bad-rate diff</th>"
        "<th>Expected issue</th><th>Detected issue</th><th>Issue match</th><th>FPS</th><th>Message</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _metric_card(label: str, value, css_class: str = "") -> str:
    return (
        '<article class="card">'
        f'<div class="metric-label">{escape(str(label))}</div>'
        f'<div class="metric-value {escape(css_class)}">{escape(str(value))}</div>'
        "</article>"
    )


def _score_class(value: Optional[float]) -> str:
    if value is None:
        return ""
    if value >= 85:
        return "good"
    if value >= 65:
        return "warn"
    return "bad"


def _count_accuracy(manual_count: int, detected_count: int) -> float:
    if manual_count == 0:
        return 100.0 if detected_count == 0 else 0.0
    return max(0.0, 100.0 * (1.0 - (abs(detected_count - manual_count) / manual_count)))


def _accuracy_from_abs_error(manual_total: int, detected_total: int, absolute_error: int) -> Optional[float]:
    if manual_total == 0:
        if detected_total == 0:
            return 100.0
        return 0.0
    return max(0.0, 100.0 * (1.0 - (absolute_error / manual_total)))


def _bad_rate(rep_count: int, bad_rep_count: int) -> Optional[float]:
    if rep_count == 0:
        return 0.0 if bad_rep_count == 0 else None
    return round((bad_rep_count / rep_count) * 100.0, 2)


def _optional_difference(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None or right is None:
        return None
    return round(left - right, 2)


def _divide_percent(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return round((numerator / denominator) * 100.0, 2)


def _average_optional(values: Iterable[Optional[float]]) -> Optional[float]:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return round(sum(clean_values) / len(clean_values), 2)


def _parse_optional_int(value) -> tuple[Optional[int], str]:
    raw = _clean(value)
    if not raw:
        return None, ""
    try:
        return int(raw), ""
    except ValueError:
        return None, f"Invalid integer value: {raw}."


def _parse_bad_sequence(value) -> tuple[tuple[bool, ...] | None, str]:
    raw = _clean(value)
    if not raw:
        return None, ""
    parts = [part for part in re.split(r"[\s,;|]+", raw) if part]
    sequence: list[bool] = []
    invalid: list[str] = []
    for part in parts:
        parsed = _parse_bool(part)
        if parsed is None:
            invalid.append(part)
        else:
            sequence.append(parsed)
    if invalid:
        return None, "Invalid manual_bad_sequence token(s): " + ", ".join(invalid) + "."
    return tuple(sequence), ""


def _parse_bool(value) -> Optional[bool]:
    raw = _clean(value).lower()
    if raw in {"1", "b", "bad", "true", "t", "yes", "y"}:
        return True
    if raw in {"0", "g", "good", "false", "f", "no", "n", "ok", "pass"}:
        return False
    return None


def _safe_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_issue(value) -> Optional[str]:
    raw = _clean(value).lower().replace("-", "_").replace(" ", "_")
    if raw in {"", "none", "n/a", "na", "no_issue", "no_issues"}:
        return None
    return raw


def _clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_blank_row(row: dict[str, str]) -> bool:
    return all(not _clean(value) for value in row.values())


def _format_optional_int(value: Optional[int]) -> str:
    return "" if value is None else str(value)


def _format_optional_float(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.2f}"


def _format_float(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value:.1f}"


def _format_percent(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value:.1f}%"


def _format_signed_float(value: Optional[float], suffix: str = "") -> str:
    return "N/A" if value is None else f"{value:+.1f}{suffix}"


def _format_count_pair(manual: Optional[int], detected: Optional[int]) -> str:
    return f"{_format_optional_int(manual) or 'N/A'} / {_format_optional_int(detected) or 'N/A'}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare manually labelled GymGuardian sessions against saved outputs.",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=DEFAULT_LABELS_FILE,
        help="Path to manual labels CSV.",
    )
    parser.add_argument(
        "--results-csv",
        type=Path,
        default=DEFAULT_RESULTS_CSV,
        help="Path for exported evaluation CSV.",
    )
    parser.add_argument(
        "--report-html",
        type=Path,
        default=DEFAULT_REPORT_HTML,
        help="Path for exported HTML report.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    results_csv, report_html = export_evaluation_report(
        labels_path=args.labels,
        results_csv_path=args.results_csv,
        report_html_path=args.report_html,
    )
    print(f"Evaluation results exported: {results_csv}")
    print(f"Evaluation report exported: {report_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
