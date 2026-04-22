# GymGuardian Test Plan

## 1. Scope

This document defines the manual test plan for the GymGuardian MVP desktop application. The current scope covers:

- Dashboard navigation
- Squat session start and end flow
- Session summary and video persistence
- Session browser navigation and open actions
- Squat rep counting accuracy
- Too-shallow form detection
- Basic performance and robustness checks using the in-app debug overlay

## 2. Test Objectives

### Functionality

- Verify the dashboard, session loop, and session browser work as expected.
- Verify sessions return to the dashboard instead of terminating the app.
- Verify saved outputs are written to the correct timestamped session folder.

### Accuracy

- Compare manual squat rep counts against app rep counts.
- Confirm shallow squats are flagged as bad reps with the correct reason.

### Performance

- Check estimated FPS using the session debug overlay.
- Confirm the app remains usable on a laptop webcam at 720p.

### Robustness

- Verify the app handles normal state transitions without crashing.
- Verify missing or incomplete session artifacts are handled gracefully in the browser.

## 3. Test Environment

| Item                    | Value                                                                                                 |
| ----------------------- | ----------------------------------------------------------------------------------------------------- |
| Operating system        | Windows 10/11 local desktop environment                                                               |
| Camera                  | Laptop webcam configured for 720p capture request                                                     |
| Python version          | Python 3.10.11                                                                                        |
| Main libraries          | `mediapipe==0.10.14`, `opencv-python==4.11.0.86`, `opencv-contrib-python==4.11.0.86`, `numpy==1.26.4` |
| Other dependencies      | See pinned versions in `requirements.txt`                                                             |
| App entry point         | `python src/app.py`                                                                                   |
| Session output location | `sessions/<YYYYMMDD_HHMMSS>/`                                                                         |

## 4. Evidence Collection

Use the following evidence types where possible:

- Screenshot of the dashboard, session overlay, browser, or debug overlay
- Saved `summary.json` file from the relevant session folder
- Saved `session.mp4` file from the relevant session folder
- Short manual observation note, including count comparison where needed

Suggested evidence naming:

- `evidence/dashboard-navigation.png`
- `evidence/session-summary-json.png`
- `evidence/browser-open-folder.png`
- `evidence/rep-count-run-01.txt`

## 5. FPS Measurement Approach

Use the debug overlay during a live session:

1. Start a session from the dashboard.
2. Press `D` to enable the debug overlay.
3. Stand in frame for 5 seconds, then perform 5 to 10 squats.
4. Observe the `FPS` line on screen for at least 10 seconds.
5. Record the typical steady FPS value, plus any noticeable drops during movement.
6. Capture a screenshot showing the debug overlay and note the lighting conditions and camera angle.

Recommended reporting format:

- Typical FPS at rest: `18`
- Typical FPS during squats: `14-16`
- Lowest observed FPS: `13`
- Notes on lag or dropped responsiveness: `Minor FPS drops observed during movement, likely due to lighting conditions and increased pose estimation complexity. No major lag or freezing observed.`

## 6. Test Cases

| ID    | Scenario                                   | Steps                                                                                                                                                                      | Expected Result                                                                                                                      | Actual Result | Evidence |
| ----- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------- | -------- |
| TC-01 | Dashboard launch and menu visibility       | 1. Run `python src/app.py`. 2. Observe the first screen.                                                                                                                   | Dashboard appears with instructions for `S`, `B`, and `Q/Esc`.                                                                       | Application launched successfully. Dashboard screen displayed with options for starting a session (S), browsing sessions (B), and quitting (Q/Esc).       | Not required (basic navigation)  |
| TC-02 | Dashboard to session navigation            | 1. From dashboard, press `S`. 2. Observe webcam session screen.                                                                                                            | App enters session mode, webcam opens, pose overlay/session UI appear.                                                               | On pressing “S”, the application entered session mode. Webcam feed opened and pose overlay with rep counter was displayed.       | Not required (basic navigation)  |
| TC-03 | Dashboard to browser navigation            | 1. From dashboard, press `B`. 2. Observe browser screen.                                                                                                                   | App enters browser mode and lists recent sessions newest first, or shows no-sessions message.                                        | On pressing “B”, the application entered browser mode and displayed a list of saved sessions sorted by most recent.       | Not required (basic navigation)  |
| TC-04 | Session end returns to dashboard           | 1. Start a session. 2. Press `Q` or `Esc`.                                                                                                                                 | Session ends, files are saved, and app returns to dashboard instead of closing completely.                                           | Pressing “Q” or “Esc” during a session ended the session, saved session data, and returned to the dashboard without closing the application.      | Not required (basic navigation)  |
| TC-05 | Summary JSON saved to timestamped folder   | 1. Start a short session. 2. End session. 3. Open latest folder in `sessions/`. 4. Inspect `summary.json`.                                                                 | New folder named `YYYYMMDD_HHMMSS` exists and contains `summary.json` with `started_at`, `rep_count`, `bad_rep_count`, and `events`. | A new timestamped folder was created under the sessions directory. The folder contained a summary.json file with fields including started_at, rep_count, bad_rep_count, and events.       | Screenshot of sessions folder and opened summary.json file.  |
| TC-06 | Session video saved to timestamped folder  | 1. Start a short session. 2. End session. 3. Inspect latest session folder.                                                                                                | Same session folder contains `session.mp4`; video opens and plays using a media player.                                              | The same session folder contained a session.mp4 file. The video opened successfully using the default media player and showed the recorded workout.       | Screenshot of session folder and video playback.  |
| TC-07 | Browser open session folder                | 1. Enter browser. 2. Select a session with Up/Down. 3. Press `O`.                                                                                                          | Windows Explorer opens the selected session folder.                                                                                  | Pressing “O” in the browser successfully opened the selected session folder in Windows Explorer.       | Screenshot of opened session folder in Windows Explorer.  |
| TC-08 | Browser open session video                 | 1. Enter browser. 2. Select a session with an existing `session.mp4`. 3. Press `P`.                                                                                        | Default Windows media player opens the selected session video.                                                                       | Pressing “P” in the browser opened the selected session.mp4 file in the default media player.       | Screenshot of video playback after selection.  |
| TC-09 | Rep counting accuracy against manual count | 1. Start a session. 2. Perform 10 clearly visible full-depth squats. 3. Count manually during the run. 4. End session and inspect on-screen/app count plus `summary.json`. | App rep count matches manual count or differs by no more than the agreed tolerance for MVP.                                          | Manual count = 10, App count = 10. No discrepancy observed, indicating accurate rep detection under controlled conditions.       | Screenshot of session overlay showing rep count and corresponding summary.json file (e.g., sessions/20260415_155017/summary.json)  |
| TC-10 | Too-shallow detection for bad reps         | 1. Start a session. 2. Perform 5 intentionally shallow squats without reaching full depth. 3. End session and inspect `summary.json`.                                      | Bad reps increase and relevant rep events indicate shallow failure reason such as `too_shallow`.                                     | App didn’t count any shallow reps at all and hence failed to classify any as bad reps. No "too_shallow" reason recorded in summary.json.       | Screenshot of summary.json showing bad_rep_count = 0 despite shallow squats.  |
| TC-11 | Mixed valid and shallow squat set          | 1. Start a session. 2. Perform 5 full squats followed by 5 shallow squats. 3. End session.                                                                                 | Total rep count reflects all valid cycles; bad rep count reflects only shallow reps.                                                 | App counted only 5 valid repetitions out of 10 (5 correct + 5 shallow). Shallow squats were not recognised as valid repetitions and were not flagged as bad reps.       | Browser screenshot showing session with 5 reps and 0 bad reps.  |
| TC-12 | Debug overlay FPS measurement              | 1. Start session. 2. Press `D`. 3. Observe overlay for at least 10 seconds while standing and squatting.                                                                   | Debug overlay toggles on, shows FPS, pose detection, knee angle, and threshold values from config.                                   | Debug overlay displayed correctly. FPS observed ~15 during testing. Performance remained stable with minor fluctuations during movement.       | Screenshot of debug overlay with FPS visible.  |
| TC-13 | Debug overlay toggle off                   | 1. During session, press `D` twice.                                                                                                                                        | Debug overlay appears on first press and disappears on second press without affecting rep counting.                                  | Debug overlay successfully toggled on first press (D) and turned off on second press. No impact on session performance or rep counting.       | Screenshot showing overlay visible and then hidden.  |
| TC-14 | Browser ordering by recency                | 1. Create two or more sessions at different times. 2. Open browser.                                                                                                        | Most recent session folder appears first in the list.                                                                                | Sessions displayed in descending order (newest first) based on timestamped folder names.       | Screenshot of browser showing latest session at top.  |
| TC-15 | Robustness when no pose is detected        | 1. Start a session. 2. Step out of camera frame or block the camera.                                                                                                       | App continues running, pose status becomes unavailable/no-pose, and no crash occurs.                                                 | When user moved out of frame, system correctly transitioned to the "no_pose" state       | Screenshot showing "State: no_pose" during session.  |

## 7. Manual Accuracy Recording Template

Use this table for repeated squat accuracy runs.

| Run ID | Session Folder | Manual Count | App Count | Difference | Manual Bad Reps | App Bad Reps | Notes   |
| ------ | -------------- | ------------ | --------- | ---------- | --------------- | ------------ | ------- |
| ACC-01 | 20260415_155017        | 10      | 10   | 0    | 0         | 0      | Normal squats — accurate |
| ACC-02 | 20260415_155411        | 5      | 0   | -5    | 5         | 0      | Shallow squats not detected |
| ACC-03 | 20260415_155611        | 10      | 5   | -5    | 5         | 0      | Shallow reps ignored |

## 8. Initial Results

Fill this section after the first manual test pass.

### Test Run Metadata

- Test date: `15/04/2026`
- Tester: `Self`
- Lighting conditions: `Indoor, moderate lighting (some instability observed)`
- Camera position/angle: `Front-facing laptop webcam`
- Distance from camera: `~1.5–2 meters`

### Summary of Outcomes

| Area                  | Result  | Notes |
| --------------------- | ------- | ----- |
| Dashboard navigation  | Pass | All transitions work correctly      |
| Session lifecycle     | Pass | Session starts and returns to dashboard      |
| Summary persistence   | Pass | summary.json created correctly      |
| Video persistence     | Pass | session.mp4 saved and playable      |
| Browser actions       | Pass | Open and playback functions work      |
| Rep counting accuracy | Pass | Accurate for correct squats      |
| Shallow detection     | Fail | Not detected or recorded      |
| FPS/performance       | Acceptable | ~15 FPS, affected by lighting      |

### Observed Issues

- `Issue 1:` `Shallow squat detection is not functioning; bad reps are not identified or recorded`
- `Issue 2:` `Shallow squats are not counted as valid repetitions, resulting in undercounting in mixed scenarios.`
- `Issue 3:` `FPS performance drops under suboptimal lighting conditions.`

### Evidence Checklist

- Dashboard screenshot: `Yes`
- Session overlay screenshot: `Yes`
- Debug overlay screenshot: `Yes`
- Browser screenshot: `Yes`
- Sample `summary.json`: `Yes`
- Sample `session.mp4`: `Yes`
