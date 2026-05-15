# GymGuardian Test Plan

## 1. Scope

This document defines the final testing approach for GymGuardian, a local OpenCV/MediaPipe desktop prototype for squat monitoring. Testing covers the complete implemented system rather than a newly trained model.

Covered areas:

- Dashboard navigation and window behaviour
- Live webcam squat analysis
- Offline local video analysis
- Pose/visibility handling
- Rep counting and bad-rep classification
- Calibration and default-threshold fallback
- Camera source selection
- Session recording and local evidence files
- Bad-rep evidence export — slow-motion clips, chapter markers, `bad_rep_timestamps`
- Session browser and analytics dashboard
- HTML analytics export and evaluation export
- Automated regression tests for deterministic logic

## 2. Test Objectives

### Functional correctness

- Verify that all major screens open from the dashboard and return safely.
- Verify that live and offline analysis reuse the same squat-analysis pipeline.
- Verify that session outputs are saved locally and can be reopened.
- Verify that invalid quick-exit sessions do not pollute meaningful analytics.

### Squat-analysis accuracy

- Compare manually labelled repetition counts against detected counts.
- Confirm full-depth squats are counted as good repetitions.
- Confirm shallow squats are counted as repetitions and classified as bad reps.
- Confirm mixed good/bad sessions produce correct total and bad-rep counts.

### Robustness and limitations

- Check behaviour under rotation, low light, partial visibility, out-of-frame movement, and different camera sources.
- Treat partial body visibility as a documented limitation when landmarks are insufficient.
- Verify that the application does not crash during invalid, incomplete, or no-pose conditions.

### Evidence and reporting

- Generate `evaluation_results.csv` and `evaluation_report.html` from manual labels.
- Capture screenshots of the final UI screens and exported reports.
- Keep evaluation claims tied to saved sessions, manual labels, and automated test output.

## 3. Test Environment

| Item | Final evaluation value |
| --- | --- |
| Operating system | Windows local desktop environment |
| Application type | Python/OpenCV desktop application |
| Python version | Python 3.10 environment used through project venv |
| Pose component | MediaPipe pose estimation |
| Primary live camera | Phone camera exposed to Windows as an external webcam |
| Comparison camera | Built-in laptop webcam |
| Offline input | Local MP4 files processed from `input_videos/` |
| Main outputs | `summary.json`, `rep_metrics.csv`, `session_report.txt`, `session.mp4` or `analysed_video.mp4`, `session_raw.mp4` (live only), `bad_reps/` clip subfolder, analytics/evaluation HTML exports |
| Evaluation label file | `docs/evaluation/manual_labels.csv` |
| Evaluation command | `python src/session/evaluation_export.py` |
| Automated test command | `python -m pytest` |

## 4. Evidence Collection

For each important manual scenario, save or reference:

- The session folder name in `sessions/`
- The saved video evidence: `session.mp4` or `analysed_video.mp4`
- The detected summary: `summary.json`
- The per-rep export: `rep_metrics.csv`
- The manual label row in `docs/evaluation/manual_labels.csv`
- Screenshots of relevant UI or exported HTML report screens

Recommended final screenshots:

- Main dashboard with camera source and calibration state
- Live session overlay with full-body landmarks
- Analytics dashboard with recent trends and session report
- Session browser showing valid sessions with average knee/FPS columns
- Settings screen showing theme, camera, browser, and calibration controls
- Exported analytics HTML report
- Exported evaluation HTML report
- Terminal output from `python -m pytest`

## 5. Manual Labelled Evaluation Dataset

The current manual label file contains 20 rows:

| Group | Cases | Purpose |
| --- | --- | --- |
| Live front-facing | L01-L03 | Full-depth, shallow, and mixed squat sets |
| Live orientation | L04-L06 | Slight right, slight left, and back-facing movement where landmarks remain usable |
| Failure/visibility | L07-L08 | No-pose/out-of-frame and partial lower-body visibility |
| Lighting | L09 | Low-light behaviour |
| Calibration | L10-L11 | Calibrated full-depth and calibrated shallow tests |
| Camera source | L12 | Built-in webcam comparison |
| Invalid quick exit | L13 | Start and exit immediately; no session folder expected |
| Longer run | L14 | 20-rep longer session with mixed issue sequence |
| Offline videos | V01-V06 | Own and friend/user videos processed through local video analysis |

`L13` is intentionally unlabelled because no session folder was created. This verifies that invalid quick-exit runs are not treated as workout data. `L07` is kept as an incomplete/no-pose case. `L08` is retained as the main partial-visibility limitation case.

## 6. Current Quantitative Results

Results generated from `docs/evaluation/manual_labels.csv` using `src/session/evaluation_export.py`:

| Metric | Current result | Interpretation |
| --- | --- | --- |
| Labelled rows | 20 | Includes live, offline, calibration, camera, failure, and quick-exit rows |
| Evaluated meaningful rows | 18 | Excludes the incomplete no-pose row and the no-session quick-exit row |
| Manual repetitions in evaluated rows | 148 | Ground truth from manual video/session review |
| Detected repetitions in evaluated rows | 144 | Four-rep loss caused by the partial-visibility limitation case |
| Aggregate rep-count accuracy | 97.3% | Calculated from absolute rep-count error |
| Controlled visible-body accuracy | 100.0% | 143 manual reps and 143 detected reps when excluding partial visibility |
| Manual bad reps | 40 | Ground truth bad-rep count |
| Detected bad reps | 40 | Detected bad-rep total matched manual labels |
| Issue match | 18/18 evaluated rows | Expected issue matched detected main issue for evaluated rows |
| Bad-rep sequence precision | 100.0% | For rows with per-rep manual bad/good sequences |
| Bad-rep sequence recall | 100.0% | For rows with per-rep manual bad/good sequences |
| Average FPS across evaluated rows | about 21.3 FPS | Mixed live, offline, and built-in camera conditions |
| Built-in webcam FPS | about 10.2 FPS in current labelled comparison | Lower image quality and lower frame rate than external phone camera |

## 7. Manual Scenario Matrix

| ID | Scenario | Manual reps | Manual bad reps | Expected issue | Evidence source |
| --- | --- | ---: | ---: | --- | --- |
| L01 | Front-facing full-depth squats | 10 | 0 | none | Live session folder |
| L02 | Front-facing shallow squats | 5 | 5 | too_shallow | Live session folder |
| L03 | Mixed front-facing full and shallow squats | 10 | 5 | too_shallow | Live session folder |
| L04 | Slight right turn | 6 | 0 | none | Live session folder |
| L05 | Slight left turn | 6 | 0 | none | Live session folder |
| L06 | Back/away-facing test | 6 | 0 | none | Live session folder |
| L07 | Out of frame / no pose | 0 | 0 | none | Incomplete/no-pose evidence |
| L08 | Partial lower-body visibility | 5 | 0 | none | Known limitation evidence |
| L09 | Low-light test | 5 | 2 | too_shallow | Live session folder |
| L10 | Calibrated full-depth squats | 10 | 0 | none | Live calibrated session |
| L11 | Calibrated shallow squats | 5 | 5 | too_shallow | Live calibrated session |
| L12 | Built-in webcam source | 5 | 0 | none | Built-in webcam comparison |
| L13 | Start and exit immediately | N/A | N/A | N/A | No session folder expected |
| L14 | Long session | 20 | 8 | too_shallow | Longer live session folder |
| V01 | Own front-facing full-depth video | 10 | 0 | none | Offline analysed video |
| V02 | Own shallow video | 5 | 5 | too_shallow | Offline analysed video |
| V03 | Own mixed full and shallow video | 10 | 5 | too_shallow | Offline analysed video |
| V04 | Friend/user A normal squats | 10 | 0 | none | Offline analysed video |
| V05 | Friend/user A shallow/mixed squats | 10 | 5 | too_shallow | Offline analysed video |
| V06 | Friend/user B normal squats | 10 | 0 | none | Offline analysed video |

## 8. Functional Test Cases

Overall manual test coverage across all modules:

| Total cases | Pass | Fail | Not run | Pass rate |
| --- | --- | --- | --- | --- |
| 180 | 166 | 1 | 13 | 92.2% |

The full case matrix is maintained in `GymGuardian_Test_Cases.xlsx`. The table below lists the core functional scenarios.

| ID | Scenario | Expected Result | Status |
| --- | --- | --- | --- |
| FT-01 | Launch dashboard | Dashboard renders with all current actions | Pass |
| FT-02 | Start live session | Camera opens and live overlay appears | Pass |
| FT-03 | Analyse local video | New `video_<timestamp>` session is saved with annotated video and summary | Pass |
| FT-04 | Open analytics dashboard | Latest meaningful session, trends, progress, and report section render | Pass |
| FT-05 | Export analytics report | `exports/analytics_report.html` is created and opens | Pass |
| FT-06 | Open session browser | Valid sessions are listed newest first | Pass |
| FT-07 | Open saved video | Browser opens selected video file | Pass |
| FT-08 | Open saved folder | Browser opens selected session folder | Pass |
| FT-09 | Open settings | Theme, camera, browser, and calibration controls render | Pass |
| FT-10 | Toggle theme | Light/dark theme changes without changing analysis logic | Pass |
| FT-11 | Switch camera source | Camera index cycles and selected camera label updates | Pass |
| FT-12 | Reset calibration | Calibration profile is removed and defaults are restored | Pass |
| FT-13 | Window minimize/maximize | Static screens redraw cleanly after restore | Pass |
| FT-14 | Window close button | Application exits safely from the close button | Pass |
| FT-15 | Quick start and exit | No meaningful workout session is created or counted | Pass |

## 9. Automated Testing

Automated tests validate deterministic project logic that can run without a webcam.

Command:

```powershell
python -m pytest
```

32 tests across 6 files, all passing:

| File | Tests | Coverage |
| --- | --- | --- |
| `test_squat_logic.py` | 9 | Angle calculation, state transitions, full-depth reps, shallow reps, no-pose reset |
| `test_bad_rep_export.py` | 13 | `bad_rep_timestamps` structure, chapter metadata format, slow-clip frame count, FFmpeg graceful skip |
| `test_analytics.py` | 3 | Meaningful-session filtering, latest/previous comparison, video-session compatibility |
| `test_user_profile.py` | 3 | Adaptive threshold generation, invalid calibration rejection, settings persistence |
| `test_session_summary.py` | 2 | `summary.json`, `rep_metrics.csv`, report output, valid-session handling |
| `test_evaluation_export.py` | 2 | Manual label parsing, missing sessions, incomplete session handling |

The automated suite supports regression testing. It does not claim to measure MediaPipe model accuracy or real webcam performance.

## 10. Known Issues and Limitations

| Limitation | Evidence | Mitigation / Report Treatment |
| --- | --- | --- |
| Partial lower-body visibility can under-count reps | L08 detected fewer reps than the manual count | Report as a camera/visibility limitation, not a hidden defect |
| Built-in webcam has lower FPS and image quality | L12 average FPS lower than phone camera source | Camera source selection allows using a better external/phone camera |
| Low light affects landmark reliability | L09 low-light scenario included | State stable lighting as an operating assumption |
| 2D angle approximation depends on camera placement | Rotation/orientation scenarios included | Use front or near-front camera setup for best results |
| This is not a medical diagnosis system | Feedback is rule-based and movement-quality focused | Use coaching/prototype wording only |

## 11. Final Evidence Checklist

- `docs/evaluation/manual_labels.csv` updated with final manual labels
- `exports/evaluation_results.csv` regenerated from the final labels
- `exports/evaluation_report.html` regenerated from the final labels
- `exports/analytics_report.html` regenerated after final sessions
- `GymGuardian_Test_Cases.xlsx` updated with final test coverage
- Terminal screenshot of automated tests
- Screenshots of the final application screens
- Sample session artefacts retained for appendix evidence
