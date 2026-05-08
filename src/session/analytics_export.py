"""HTML export helpers for GymGuardian analytics evidence."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from core.paths import PROJECT_ROOT
from session.browser import AnalyticsSnapshot


EXPORTS_DIR = PROJECT_ROOT / "exports"
DEFAULT_ANALYTICS_REPORT = EXPORTS_DIR / "analytics_report.html"


def export_analytics_report(
    snapshot: AnalyticsSnapshot,
    output_path: Path = DEFAULT_ANALYTICS_REPORT,
    calibration_profile=None,
) -> Path:
    """Write a polished project-level analytics report and return its path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        _build_html(snapshot, calibration_profile),
        encoding="utf-8",
    )
    return output_path


def _build_html(snapshot: AnalyticsSnapshot, calibration_profile=None) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    calibration_status = "Calibrated" if calibration_profile else "Default thresholds"
    latest_session = _format_timestamp(snapshot.latest_timestamp)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GymGuardian Analytics Report</title>
  <style>
    :root {{
      --bg: #eef5ef;
      --panel: #ffffff;
      --panel-soft: #f5faf6;
      --ink: #20332a;
      --muted: #617268;
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
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 40px 28px 56px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-start;
      margin-bottom: 26px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 42px;
      letter-spacing: -0.04em;
    }}
    h2 {{
      margin: 0 0 16px;
      font-size: 22px;
      letter-spacing: -0.02em;
    }}
    p {{ margin: 0; color: var(--muted); line-height: 1.55; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 8px 14px;
      background: var(--green-soft);
      color: var(--green);
      font-weight: 700;
      white-space: nowrap;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      margin: 24px 0;
    }}
    .card {{
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 22px;
      box-shadow: var(--shadow);
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .metric-value {{
      margin-top: 10px;
      font-size: 30px;
      font-weight: 800;
      letter-spacing: -0.03em;
    }}
    .section {{
      margin-top: 18px;
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      box-shadow: var(--shadow);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 16px;
    }}
    th, td {{
      text-align: left;
      padding: 13px 12px;
      border-bottom: 1px solid #d8e4da;
      font-size: 14px;
    }}
    th {{
      color: var(--muted);
      background: var(--panel-soft);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-size: 12px;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .split {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }}
    .issue-row {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      padding: 12px 0;
      border-bottom: 1px solid #d8e4da;
    }}
    .issue-row:last-child {{ border-bottom: 0; }}
    .note {{
      margin-top: 20px;
      padding: 16px 18px;
      border-left: 5px solid var(--green);
      background: #edf7ef;
      border-radius: 14px;
    }}
    .good {{ color: var(--green); }}
    .warn {{ color: var(--amber); }}
    .bad {{ color: var(--red); }}
    @media (max-width: 860px) {{
      header, .split {{ grid-template-columns: 1fr; display: grid; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>GymGuardian Analytics Report</h1>
        <p>Project-level squat coaching analytics generated from local session summaries.</p>
      </div>
      <div class="badge">{escape(calibration_status)}</div>
    </header>

    <section class="grid">
      {_metric_card("Generated", generated_at)}
      {_metric_card("Total sessions", snapshot.total_sessions)}
      {_metric_card("Meaningful sessions", snapshot.meaningful_session_count)}
      {_metric_card("Latest session", latest_session)}
      {_metric_card("Latest reps", _display(snapshot.latest_rep_count))}
      {_metric_card("Latest bad reps", _display(snapshot.latest_bad_rep_count), "bad" if (snapshot.latest_bad_rep_count or 0) > 0 else "")}
      {_metric_card("Bad rep rate", _format_percentage(snapshot.latest_bad_rep_percentage), "warn" if (snapshot.latest_bad_rep_percentage or 0) > 0 else "")}
      {_metric_card("Average FPS", _format_fps(snapshot.latest_avg_fps))}
    </section>

    <section class="section">
      <h2>Recent Meaningful Session Trends</h2>
      {_trend_table(snapshot)}
    </section>

    <section class="section split">
      <div>
        <h2>Issue Breakdown</h2>
        {_issue_breakdown(snapshot)}
      </div>
      <div>
        <h2>Recommendation</h2>
        <p><strong>Main concern:</strong> {escape(snapshot.main_concern or "N/A")}</p>
        <p><strong>Suggested improvement:</strong> {escape(snapshot.suggested_improvement or "N/A")}</p>
        <p><strong>Focus area:</strong> {escape(snapshot.focus_area or "N/A")}</p>
        <div class="note">
          Incomplete sessions are kept on disk but ignored for meaningful-session analytics.
        </div>
      </div>
    </section>
  </main>
</body>
</html>
"""


def _metric_card(label: str, value, css_class: str = "") -> str:
    return (
        '<article class="card">'
        f'<div class="metric-label">{escape(str(label))}</div>'
        f'<div class="metric-value {escape(css_class)}">{escape(str(value))}</div>'
        "</article>"
    )


def _trend_table(snapshot: AnalyticsSnapshot) -> str:
    if not snapshot.trend_sessions:
        return "<p>No meaningful session data available yet.</p>"

    rows = []
    for item in snapshot.trend_sessions:
        rows.append(
            "<tr>"
            f"<td>{escape(_format_timestamp(item.folder_name))}</td>"
            f"<td>{item.rep_count}</td>"
            f"<td>{item.bad_rep_count}</td>"
            f"<td>{escape(_format_percentage(item.bad_rep_percentage))}</td>"
            f"<td>{escape(_format_angle(item.avg_knee_angle))}</td>"
            f"<td>{escape(_format_angle(item.avg_ankle_angle))}</td>"
            f"<td>{escape(_format_angle(item.avg_torso_angle))}</td>"
            f"<td>{escape(_format_fps(item.avg_fps))}</td>"
            f"<td>{escape(_format_issue(item.most_common_issue))}</td>"
            "</tr>"
        )

    return (
        "<table>"
        "<thead><tr>"
        "<th>Session</th><th>Reps</th><th>Bad</th><th>Bad rate</th>"
        "<th>Avg knee</th><th>Avg ankle</th><th>Torso</th><th>FPS</th><th>Issue</th>"
        "</tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _issue_breakdown(snapshot: AnalyticsSnapshot) -> str:
    if not snapshot.issue_totals:
        return "<p>No repeated form issue has been recorded across meaningful sessions.</p>"

    rows = []
    for issue, count in list(snapshot.issue_totals.items())[:6]:
        rows.append(
            '<div class="issue-row">'
            f"<span>{escape(_format_issue(issue))}</span>"
            f"<strong>{count}</strong>"
            "</div>"
        )
    return "".join(rows)


def _display(value) -> str:
    if value is None:
        return "N/A"
    return str(value)


def _format_percentage(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _format_angle(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f} deg"


def _format_fps(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}"


def _format_issue(value: str | None) -> str:
    if not value:
        return "none"
    return value.replace("_", " ")


def _format_timestamp(value: str | None) -> str:
    if not value:
        return "N/A"
    if len(value) == 15 and "_" in value:
        date_part, time_part = value.split("_", maxsplit=1)
        if len(date_part) == 8 and len(time_part) == 6:
            return (
                f"{date_part[0:4]}-{date_part[4:6]}-{date_part[6:8]} "
                f"{time_part[0:2]}:{time_part[2:4]}:{time_part[4:6]}"
            )
    return value
