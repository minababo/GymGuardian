# GymGuardian Evaluation Labels

This folder stores manual labels used by the evaluation harness. The harness compares these labels against saved GymGuardian session outputs in `sessions/<timestamp>/`.

## How to label a session

1. Open the saved session video — `session.mp4` for live sessions or `analysed_video.mp4` for offline video analysis sessions.
2. Count the visible completed squat repetitions manually.
3. Count how many of those repetitions should be treated as bad reps.
4. Add one row to `manual_labels.csv`.
5. Run the evaluator:

```powershell
.\venv\Scripts\python.exe src\session\evaluation_export.py
```

Outputs are written to:

- `exports/evaluation_results.csv`
- `exports/evaluation_report.html`

## CSV columns

| Column | Meaning |
| --- | --- |
| `case_id` | Test case or scenario ID, for example `S1-R1`. |
| `scenario` | Human-readable scenario, for example `Full-depth squats`. |
| `session_folder` | Folder name under `sessions/`, for example `20260508_230034`. |
| `manual_rep_count` | Manual repetition count from reviewing the video. |
| `manual_bad_rep_count` | Manual bad-repetition count from reviewing the video. |
| `expected_issue` | Expected main issue, for example `too_shallow`, `ankle_control`, `torso_lean`, or `none`. |
| `manual_bad_sequence` | Optional per-rep sequence using `0` for good and `1` for bad, for example `0,0,1,1`. |
| `lighting` | Lighting condition used during the test. |
| `camera_angle` | Camera position, for example `front-facing`, `rotated`, or `partial-body`. |
| `notes` | Short observation notes. |

## Important note

This evaluates the system-level output of GymGuardian. It does not train or validate a custom machine-learning model. Manual video labels are treated as the ground truth for report metrics such as rep count accuracy, bad-rep count error, issue match, and FPS.
