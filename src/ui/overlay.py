"""Overlay rendering for workout, dashboard, and browser screens."""

from __future__ import annotations

import cv2


class OverlayRenderer:
    def draw(self, frame_bgr, results, squat_state, rep_counter=None) -> None:
        # results.pose_landmarks is a list (per detected pose), each is list of landmarks
        if results and getattr(results, "pose_landmarks", None):
            if len(results.pose_landmarks) > 0:
                landmarks = results.pose_landmarks[0]
                h, w = frame_bgr.shape[:2]

                for lm in landmarks:
                    x = int(lm.x * w)
                    y = int(lm.y * h)
                    cv2.circle(frame_bgr, (x, y), 3, (0, 255, 0), -1)

        label = f"State: {squat_state.label}"
        if squat_state.knee_angle is not None:
            label = f"{label} | knee: {squat_state.knee_angle:.1f}"

        cv2.putText(
            frame_bgr,
            label,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        if rep_counter is not None:
            rep_text = (
                f"Reps: {rep_counter.rep_count} | "
                f"Bad: {rep_counter.bad_rep_count} | "
                f"Last: {rep_counter.last_rep_result}"
            )
            cv2.putText(
                frame_bgr,
                rep_text,
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

    def draw_dashboard(self, frame_bgr) -> None:
        self._put_heading(frame_bgr, "GymGuardian Dashboard")
        lines = [
            "S - Start Session",
            "B - Browse Sessions",
            "Q / Esc - Quit",
        ]
        self._put_lines(frame_bgr, lines, start_y=170)

    def draw_browser(self, frame_bgr, sessions, selected_index: int) -> None:
        self._put_heading(frame_bgr, "Session Browser")
        instructions = [
            "Up/Down - Move selection",
            "P - Play session.mp4",
            "O - Open session folder",
            "Backspace - Return to Dashboard",
        ]
        self._put_lines(frame_bgr, instructions, start_y=110, line_height=28, scale=0.7)

        if not sessions:
            self._put_lines(frame_bgr, ["No sessions found in /sessions"], start_y=260)
            return

        start = max(0, selected_index - 5)
        end = min(len(sessions), start + 10)
        row_y = 260
        for idx in range(start, end):
            item = sessions[idx]
            selected = idx == selected_index
            prefix = ">" if selected else " "
            reps = "?" if item.rep_count is None else str(item.rep_count)
            bad = "?" if item.bad_rep_count is None else str(item.bad_rep_count)
            text = f"{prefix} {item.folder_name} | reps: {reps} | bad: {bad}"
            color = (0, 255, 255) if selected else (200, 200, 200)
            cv2.putText(
                frame_bgr,
                text,
                (30, row_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                color,
                2,
                cv2.LINE_AA,
            )
            row_y += 36

    def _put_heading(self, frame_bgr, text: str) -> None:
        cv2.putText(
            frame_bgr,
            text,
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    def _put_lines(
        self,
        frame_bgr,
        lines: list[str],
        start_y: int,
        line_height: int = 34,
        scale: float = 0.8,
    ) -> None:
        y = start_y
        for line in lines:
            cv2.putText(
                frame_bgr,
                line,
                (30, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                scale,
                (200, 200, 200),
                2,
                cv2.LINE_AA,
            )
            y += line_height
