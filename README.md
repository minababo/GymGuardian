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
- analytics dashboard for:
  - latest meaningful session metrics
  - progress vs previous meaningful session
  - recommendation-style session insights
- session browser for opening saved videos and folders

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
- `B`: browse saved sessions
- `A`: open analytics dashboard
- `Esc`: go back or exit
- `D`: toggle debug overlay during a live session

## Camera Assumptions

The current prototype assumes:

- a single front-facing or near-front-facing webcam
- stable indoor lighting
- the full lower body remains visible during the squat
- no medical or professional coaching guarantee

## Documentation

- `docs/final-project-artifacts.md`: architecture, workflow, methodology, and project considerations
- `docs/test-plan.md`: evaluation matrix, evidence checklist, and report-ready results table

## Project Status

This repository represents a prototype-level academic system developed for the PUSL3190 Computing Project module.

## License

This project is intended for academic use.
