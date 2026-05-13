# GymGuardian

GymGuardian is a desktop-based real-time squat monitoring and analytics system built for a final-year computing project. The current project scope is intentionally narrow: one exercise, one camera, and one rule-based coaching pipeline focused on squat quality.

## Project Positioning

GymGuardian is treated as a specialized squat-coaching prototype rather than a generic fitness platform. The project prioritizes:

- robust squat rep counting
- rule-based form checks for depth, ankle control, and torso lean
- meaningful-session analytics and progress tracking
- evidence exports that support academic evaluation

Multi-exercise support is considered future work.

## Current Features

- real-time pose detection using MediaPipe and OpenCV
- squat state classification with smoothed joint-angle analysis
- rep counting driven by knee-angle state transitions
- rule-based form checks for:
  - `too_shallow`
  - `ankle_control`
  - `torso_lean`
- saved session artifacts per run:
  - `summary.json`
  - `rep_metrics.csv`
  - `session_report.txt`
  - `session.mp4`
- local video analysis for MP4 files placed in `input_videos/`
- analytics dashboard for:
  - latest meaningful session metrics
  - progress vs previous meaningful session
  - recommendation-style session insights
  - HTML analytics export
- manual-label evaluation export for report evidence
- session browser for opening saved videos and folders
- camera source switching for built-in, external USB, or virtual phone cameras
- local calibration and light/dark theme settings

## Technology Stack

- Python 3.x
- MediaPipe
- OpenCV
- NumPy

## Repository Structure

```text
GymGuardian/
|-- docs/
|   |-- final-project-artifacts.md
|   `-- test-plan.md
|-- src/
|   |-- analysis/
|   |-- core/
|   |-- pose/
|   |-- session/
|   |-- ui/
|   `-- app.py
|-- requirements.txt
`-- README.md
```

## Running the Application

### Prerequisites

- Python 3.9 or later
- Windows desktop/laptop environment
- Webcam with the user's lower body clearly visible

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

Controls:

- `S`: start squat session
- `V`: analyse newest local video in `input_videos/`
- `C`: calibrate squat depth
- `B`: browse saved sessions
- `A`: open analytics dashboard
- `G`: open settings
- `K`: switch camera source from dashboard/settings
- `Esc`: go back or exit
- `D`: toggle debug overlay during a live session

### Build a Windows executable

The project can be packaged as a local Windows desktop executable with the
GymGuardian icon applied to the title bar and taskbar.

```powershell
.\scripts\build_exe.ps1
```

The generated application is written to:

```text
dist\GymGuardian\GymGuardian.exe
```

The build script installs PyInstaller into the active Python environment if it
is missing. Runtime outputs such as `sessions/`, `exports/`, `user_data/`, and
`input_videos/` remain local to the executable folder when running the packaged
app.

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
