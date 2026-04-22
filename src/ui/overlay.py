"""Overlay rendering for workout, dashboard, and browser screens."""

from __future__ import annotations

import cv2


class OverlayRenderer:
    def draw(
        self,
        frame_bgr,
        results,
        squat_state,
        rep_counter=None,
        feedback_message: str | None = None,
        feedback_level: str = "info",
    ) -> None:
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

        if feedback_message:
            self._draw_feedback(frame_bgr, feedback_message, feedback_level)

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

    def draw_debug(self, frame_bgr, debug_info: dict) -> None:
        lines = [
            "DEBUG (D to toggle)",
            f"FPS: {debug_info.get('fps', 0.0):.1f}",
            f"Pose detected: {'yes' if debug_info.get('pose_detected') else 'no'}",
        ]

        knee_angle = debug_info.get("knee_angle")
        if knee_angle is None:
            lines.append("Knee angle: n/a")
        else:
            lines.append(f"Knee angle: {knee_angle:.1f}")

        lines.extend(
            [
                f"down_knee_angle: {debug_info.get('down_knee_angle')}",
                f"up_knee_angle: {debug_info.get('up_knee_angle')}",
                f"rep_bottom_knee_angle: {debug_info.get('rep_bottom_knee_angle')}",
                f"shallow_knee_angle: {debug_info.get('shallow_knee_angle')}",
                f"down_hold_frames: {debug_info.get('down_hold_frames')}",
                f"min_rep_seconds: {debug_info.get('min_rep_seconds')}",
            ]
        )

        panel_x = 20
        panel_y = 110
        line_height = 24
        panel_w = 440
        panel_h = 20 + line_height * len(lines)
        cv2.rectangle(
            frame_bgr,
            (panel_x, panel_y),
            (panel_x + panel_w, panel_y + panel_h),
            (20, 20, 20),
            -1,
        )
        cv2.rectangle(
            frame_bgr,
            (panel_x, panel_y),
            (panel_x + panel_w, panel_y + panel_h),
            (0, 180, 255),
            2,
        )

        y = panel_y + 24
        for line in lines:
            cv2.putText(
                frame_bgr,
                line,
                (panel_x + 10, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (235, 235, 235),
                1,
                cv2.LINE_AA,
            )
            y += line_height

    def _draw_feedback(
        self, frame_bgr, message: str, feedback_level: str = "info"
    ) -> None:
        colors = {
            "ok": (0, 220, 0),
            "bad": (0, 0, 255),
            "warning": (0, 210, 255),
            "info": (235, 235, 235),
        }
        color = colors.get(feedback_level, colors["info"])
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 1.0
        thickness = 2
        text_size, _ = cv2.getTextSize(message, font, scale, thickness)
        text_w, text_h = text_size
        _, frame_w = frame_bgr.shape[:2]
        pad_x = 16
        pad_y = 12
        panel_x = max(20, frame_w - text_w - (pad_x * 2) - 24)
        panel_y = 24
        panel_w = text_w + (pad_x * 2)
        panel_h = text_h + (pad_y * 2)

        cv2.rectangle(
            frame_bgr,
            (panel_x, panel_y),
            (panel_x + panel_w, panel_y + panel_h),
            (20, 20, 20),
            -1,
        )
        cv2.rectangle(
            frame_bgr,
            (panel_x, panel_y),
            (panel_x + panel_w, panel_y + panel_h),
            color,
            2,
        )
        cv2.putText(
            frame_bgr,
            message,
            (panel_x + pad_x, panel_y + pad_y + text_h),
            font,
            scale,
            color,
            thickness,
            cv2.LINE_AA,
        )

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
