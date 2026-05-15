# GymGuardian

GymGuardian is a desktop-based real-time squat monitoring and analytics system built for a final-year computing project. The current project scope is intentionally narrow: one exercise, one camera, and one rule-based coaching pipeline focused on squat quality.

## Project Positioning

GymGuardian is treated as a specialized squat-coaching prototype rather than a generic fitness platform. The project prioritizes:

- robust squat rep counting
- rule-based form checks for depth, ankle control, and torso lean
- meaningful-session analytics and progress tracking
- evidence exports that support academic evaluation

Multi-exercise support is considered future work.

## Features

- real-time pose detection using MediaPipe and OpenCV
- squat state classification with smoothed joint-angle analysis
- rep counting driven by knee-angle state transitions
- rule-based form checks:
  - `too_shallow` — knee did not reach full depth (bad rep, counts against session quality)
  - `ankle_control` — limited ankle bend detected (advisory warning)
  - `torso_lean` — excessive forward lean detected (advisory warning)
- bad-rep evidence export after every session:
  - slow-motion clip at 0.25x speed per flagged rep saved in a `bad_reps` subfolder
  - each clip covers the rep with a short buffer before and after
  - issue label and minimum knee angle drawn on each clip frame
  - FFmpeg chapter markers embedded into the main session video if FFmpeg is installed
  - `bad_rep_timestamps` array written to `summary.json` for machine-readable access
- session artefacts saved after every valid session:
  - `summary.json` — full metrics including rep count, issue counts, and angle averages
  - `rep_metrics.csv` — per-rep breakdown with timestamps, issues, and angle data
  - `session_report.txt` — human-readable session summary and recommendation
  - session video with pose landmarks rendered
  - `session_raw.mp4` (live sessions only) — clean unoverlay video used for clip extraction
- offline video analysis for local MP4, AVI, MOV, MKV, and M4V files
- analytics dashboard:
  - latest meaningful session metrics
  - progress vs previous meaningful session
  - recommendation-style session insights
  - HTML analytics export
- manual-label evaluation harness — reads `manual_labels.csv`, exports `evaluation_results.csv` and `evaluation_report.html`
- session browser for replaying saved videos and opening session folders
- camera source switching for built-in, external USB, or virtual phone cameras
- user calibration to derive personalised thresholds from sample squats
- light and dark theme setting

## Technology Stack

- Python 3.10
- MediaPipe
- OpenCV
- NumPy
- Pillow

## Repository Structure

```text
GymGuardian/
|-- docs/
|   |-- evaluation/
|   |-- final-project-artifacts.md
|   `-- test-plan.md
|-- scripts/
|-- src/
|   |-- analysis/
|   |-- core/
|   |-- pose/
|   |-- session/
|   |-- ui/
|   `-- app.py
|-- tests/
|-- requirements.txt
`-- README.md
```

## Running the Application

### Prerequisites

- Python 3.10
- Windows desktop or laptop
- Webcam with the lower body clearly visible during squats
- (Optional) FFmpeg on the system PATH — required only for embedding chapter markers into session videos

### Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Start the app

```bash
python src/app.py
```

The dashboard opens. Use keyboard shortcuts to navigate.

**Dashboard**

| Key | Action |
| --- | --- |
| `S` | Start a live squat session |
| `V` | Analyse the most recently placed local video file |
| `C` | Run calibration to set personalised thresholds |
| `A` | Open the analytics dashboard |
| `B` | Open the session browser |
| `G` | Open settings |
| `K` | Switch camera source |
| `Esc` | Exit the application |

**During a live session**

| Key | Action |
| --- | --- |
| `D` | Toggle debug overlay |
| `Esc` | End session and save |

**Session browser**

| Key | Action |
| --- | --- |
| `P` | Play the selected session video |
| `O` | Open the selected session folder |
| `H` | Toggle hide-incomplete-sessions filter |
| `Esc` | Return to dashboard |

**Analytics dashboard**

| Key | Action |
| --- | --- |
| `R` | Refresh analytics from saved sessions |
| `E` | Export analytics report |
| `Esc` | Return to dashboard |

**Settings screen**

| Key | Action |
| --- | --- |
| `T` | Toggle light/dark theme |
| `H` | Toggle hide-incomplete-sessions in the browser |
| `K` | Switch camera source |
| `R` | Reset calibration profile to defaults |
| `Esc` | Return to dashboard |

### Build a Windows executable

The project can be packaged as a local Windows desktop executable with the GymGuardian icon applied to the title bar and taskbar.

```powershell
.\scripts\build_exe.ps1
```

The build script installs PyInstaller into the active Python environment if it is missing. Runtime outputs such as sessions, exports, user data, and input videos remain local to the executable folder when running the packaged app.

## Squat Analysis Thresholds

Default thresholds used by the rule-based analysis pipeline:

| Parameter | Default | Role |
| --- | --- | --- |
| Standing gate | 160° | Knee angle at which standing is confirmed |
| Down gate | 105° | Knee angle at which the squat bottom is confirmed |
| Early bottom gate | 150° | Minimum knee angle to confirm a rep bottom |
| Shallow flag | 110° | Knee threshold for `too_shallow` bad-rep classification |
| Ankle advisory | 172° | Ankle angle threshold for `ankle_control` warning |
| Torso advisory | 34° | Torso lean threshold for `torso_lean` warning |

When a calibration profile is saved, thresholds are derived from the user's own sample squats rather than the fixed defaults.

## Calibration

The calibration routine runs for 12 seconds of continuous squatting. It requires at least 30 pose samples and at least 25° of knee-angle movement. On completion, personalised thresholds are saved and used in place of the defaults until reset.

## Testing

```bash
python -m pytest
```

32 automated tests across 6 test files, all passing:

| File | Tests | Coverage |
| --- | --- | --- |
| `test_squat_logic.py` | 9 | Angle calculation, state transitions, rep counting, shallow detection, no-pose reset |
| `test_bad_rep_export.py` | 13 | Timestamp structure, chapter metadata format, slow-clip frame count, FFmpeg graceful skip |
| `test_analytics.py` | 3 | Meaningful-session filtering, progress comparison, video-session compatibility |
| `test_user_profile.py` | 3 | Calibration threshold generation, settings persistence |
| `test_session_summary.py` | 2 | JSON/CSV/report output, invalid-session handling |
| `test_evaluation_export.py` | 2 | Label parsing, missing and incomplete session handling |

## Camera Assumptions

The current prototype assumes:

- a single front-facing or near-front-facing webcam
- stable indoor lighting
- the full lower body remains visible during the squat
- no medical or professional coaching guarantee

## Documentation

- `docs/test-plan.md`: evaluation matrix, evidence checklist, and report-ready results table
- `docs/evaluation/`: manual-label evaluation input and instructions

Generated session folders, input videos and exports are intentionally ignored by Git.

## Project Status

This repository represents a prototype-level academic system developed for the PUSL3190 Computing Project module.

## License

This project is intended for academic use.
