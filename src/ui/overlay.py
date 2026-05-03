"""Overlay rendering for workout, dashboard, analytics, and browser screens."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class OverlayRenderer:
    """Draw OpenCV UI screens without changing app behavior."""

    FONT = cv2.FONT_HERSHEY_DUPLEX
    FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
    FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")

    # Shared visual system. OpenCV uses BGR tuples.
    BG = (229, 237, 233)
    BG_SOFT = (218, 231, 225)
    PANEL = (252, 253, 251)
    PANEL_ALT = (237, 244, 240)
    PANEL_STRONG = (221, 238, 229)
    SELECTED = (199, 229, 213)
    BORDER = (164, 187, 176)
    BORDER_ACTIVE = (76, 145, 91)

    PRIMARY = (54, 126, 72)
    PRIMARY_SOFT = (191, 224, 205)
    WARNING = (0, 143, 204)
    ERROR = (76, 86, 205)
    INFO = (196, 127, 66)
    TEXT = (25, 35, 32)
    MUTED = (76, 91, 86)
    MUTED_DARK = (124, 139, 133)
    LIVE_PANEL = (36, 47, 49)
    LIVE_CARD = (48, 60, 62)
    LIVE_BORDER = (102, 218, 150)
    LIVE_TEXT = (244, 248, 246)
    LIVE_MUTED = (178, 194, 190)
    SHADOW = (0, 0, 0)

    def draw(
        self,
        frame_bgr,
        results,
        squat_state,
        rep_counter=None,
        feedback_message: str | None = None,
        feedback_level: str = "info",
    ) -> None:
        self._draw_pose_points(frame_bgr, results)
        self._draw_session_panel(
            frame_bgr,
            squat_state,
            rep_counter,
            feedback_message,
            feedback_level,
        )

    def draw_dashboard(self, frame_bgr) -> None:
        self._fill_background(frame_bgr)
        frame_h, frame_w = frame_bgr.shape[:2]

        shell_w = min(frame_w - 96, max(1120, int(frame_w * 0.78)))
        shell_h = min(frame_h - 150, max(560, int(frame_h * 0.58)))
        shell_x = (frame_w - shell_w) // 2
        shell_y = max(120, (frame_h - shell_h) // 2 + 28)

        self._draw_panel(
            frame_bgr,
            shell_x,
            shell_y,
            shell_w,
            shell_h,
            color=self.PANEL,
            border_color=self.BORDER_ACTIVE,
            alpha=0.96,
            radius=22,
        )
        cv2.line(
            frame_bgr,
            (shell_x + 26, shell_y + 24),
            (shell_x + 26, shell_y + shell_h - 24),
            self.PRIMARY,
            3,
        )

        self._draw_pill(
            frame_bgr,
            shell_x + 58,
            shell_y + 46,
            "Desktop squat coach",
            self.PRIMARY,
            self.SELECTED,
        )

        self._put_text(
            frame_bgr,
            "GymGuardian",
            shell_x + 58,
            shell_y + 126,
            scale=1.7,
            color=self.PRIMARY,
            thickness=2,
            max_width=shell_w - 116,
        )
        self._put_text(
            frame_bgr,
            "Real-time form feedback, local session evidence, and progress analytics.",
            shell_x + 62,
            shell_y + 172,
            scale=0.58,
            color=self.MUTED,
            thickness=1,
            max_width=shell_w - 124,
        )

        insight_w = 250
        insight_gap = 14
        insight_x = shell_x + shell_w - (insight_w * 2) - insight_gap - 48
        insight_y = shell_y + 50
        self._draw_info_card(
            frame_bgr, insight_x, insight_y, insight_w, "Scope", "Squat analysis only"
        )
        self._draw_info_card(
            frame_bgr,
            insight_x + insight_w + insight_gap,
            insight_y,
            insight_w,
            "Processing",
            "Local webcam pipeline",
        )

        options = [
            ("S", "Start squat session", "Open webcam and begin form tracking"),
            ("A", "Open analytics dashboard", "View progress and recommendations"),
            ("B", "Browse saved sessions", "Review videos and session files"),
            ("Esc", "Quit application", "Close GymGuardian"),
        ]

        card_gap = 18
        cards_x = shell_x + 58
        cards_y = shell_y + 246
        card_w = (shell_w - 116 - card_gap) // 2
        card_h = 84
        for index, (key, title, subtitle) in enumerate(options):
            col = index % 2
            row = index // 2
            self._draw_action_card(
                frame_bgr,
                cards_x + ((card_w + card_gap) * col),
                cards_y + ((card_h + card_gap) * row),
                card_w,
                card_h,
                key,
                title,
                subtitle,
            )

        self._put_text(
            frame_bgr,
            "Keyboard controlled desktop prototype. Use Esc to return from any screen.",
            shell_x + 62,
            shell_y + shell_h - 34,
            scale=0.47,
            color=self.MUTED,
            thickness=1,
            max_width=shell_w - 124,
        )

    def draw_browser(self, frame_bgr, sessions, selected_index: int) -> None:
        self._fill_background(frame_bgr)
        frame_h, frame_w = frame_bgr.shape[:2]
        margin = 34

        self._draw_screen_header(
            frame_bgr,
            margin,
            "Session Browser",
            "Up/Down select  |  P play video  |  O open folder  |  Esc dashboard",
        )

        list_x = margin
        list_y = 126
        list_w = frame_w - (margin * 2)
        list_h = frame_h - list_y - margin
        status_x = list_x + list_w - 196
        status_w = 150
        bad_x = list_x + list_w - 318
        reps_x = list_x + list_w - 440
        metric_w = 70
        timestamp_w = max(260, reps_x - list_x - 56)

        self._draw_panel(
            frame_bgr,
            list_x,
            list_y,
            list_w,
            list_h,
            color=self.PANEL,
            border_color=self.BORDER,
            alpha=0.95,
        )

        if not sessions:
            self._draw_empty_state(
                frame_bgr,
                list_x,
                list_y,
                list_w,
                "No saved sessions found",
                "Complete a workout session to populate this browser.",
            )
            return

        header_y = list_y + 40
        self._put_text(frame_bgr, "Session", list_x + 28, header_y, 0.52, self.MUTED)
        self._put_text_centered(
            frame_bgr, "Reps", reps_x, header_y - 22, metric_w, 24, 0.52, self.MUTED
        )
        self._put_text_centered(
            frame_bgr, "Bad", bad_x, header_y - 22, metric_w, 24, 0.52, self.MUTED
        )
        self._put_text_centered(
            frame_bgr, "Status", status_x, header_y - 22, status_w, 24, 0.52, self.MUTED
        )
        cv2.line(
            frame_bgr,
            (list_x + 22, list_y + 58),
            (list_x + list_w - 22, list_y + 58),
            self.BORDER,
            1,
        )

        max_rows = max(1, (list_h - 88) // 50)
        start = min(
            max(0, selected_index - max_rows // 2),
            max(0, len(sessions) - max_rows),
        )
        end = min(len(sessions), start + max_rows)
        row_y = list_y + 94
        row_h = 44

        for idx in range(start, end):
            item = sessions[idx]
            selected = idx == selected_index
            reps = "N/A" if item.rep_count is None else str(item.rep_count)
            bad = "N/A" if item.bad_rep_count is None else str(item.bad_rep_count)
            is_valid = bool(
                getattr(item, "valid_session", item.rep_count not in (None, 0))
            )
            status_text = "Complete" if is_valid else "Incomplete"
            row_color = (
                self.SELECTED
                if selected
                else (235, 246, 238)
                if is_valid
                else (246, 249, 247)
            )
            border_color = (
                self.BORDER_ACTIVE
                if selected
                else (142, 186, 151)
                if is_valid
                else self.BORDER
            )

            self._draw_panel(
                frame_bgr,
                list_x + 16,
                row_y - 30,
                list_w - 32,
                row_h,
                color=row_color,
                border_color=border_color,
                alpha=0.94,
            )
            if selected:
                cv2.line(
                    frame_bgr,
                    (list_x + 30, row_y - 22),
                    (list_x + 30, row_y + 8),
                    self.PRIMARY,
                    5,
                )

            primary_color = self.TEXT if selected or is_valid else self.MUTED_DARK
            metric_color = self.TEXT if selected or is_valid else self.MUTED
            status_color = self.PRIMARY if is_valid else self.INFO
            self._put_text(
                frame_bgr,
                item.folder_name,
                list_x + 34,
                row_y,
                scale=0.62,
                color=primary_color,
                thickness=1,
                max_width=timestamp_w,
            )
            self._put_text_centered(
                frame_bgr,
                reps,
                reps_x,
                row_y - 28,
                metric_w,
                row_h,
                0.62,
                metric_color,
            )
            self._put_text_centered(
                frame_bgr,
                bad,
                bad_x,
                row_y - 28,
                metric_w,
                row_h,
                0.62,
                self.ERROR if bad not in ("0", "N/A") else metric_color,
            )
            self._draw_panel(
                frame_bgr,
                status_x,
                row_y - 25,
                status_w,
                28,
                color=(207, 235, 216) if is_valid else (236, 242, 242),
                border_color=(86, 158, 101) if is_valid else (166, 176, 174),
                alpha=0.96,
                radius=14,
            )
            self._put_text_centered(
                frame_bgr,
                status_text,
                status_x,
                row_y - 25,
                status_w,
                28,
                0.42,
                status_color,
            )
            row_y += 50

    def draw_analytics(self, frame_bgr, snapshot) -> None:
        self._fill_background(frame_bgr)
        frame_h, frame_w = frame_bgr.shape[:2]
        margin = 30

        self._draw_screen_header(
            frame_bgr,
            margin,
            "Analytics Dashboard",
            "R refresh  |  Esc dashboard",
        )

        summary_x = margin
        summary_y = 118
        summary_w = frame_w - (margin * 2)
        summary_h = 338
        lower_y = summary_y + summary_h + 18
        lower_h = frame_h - lower_y - margin

        self._draw_panel(
            frame_bgr,
            summary_x,
            summary_y,
            summary_w,
            summary_h,
            color=self.PANEL,
            border_color=self.BORDER,
            alpha=0.95,
        )
        self._put_text(
            frame_bgr,
            "Latest Meaningful Session",
            summary_x + 26,
            summary_y + 36,
            scale=0.72,
            color=self.TEXT,
            thickness=1,
            max_width=summary_w - 52,
        )

        has_meaningful_data = snapshot.meaningful_session_count > 0
        if not has_meaningful_data:
            self._draw_empty_state(
                frame_bgr,
                summary_x,
                summary_y,
                summary_w,
                "No meaningful session data available",
                "Saved folders are ignored until at least one rep is completed.",
            )
            return

        timestamp_text = self._format_session_timestamp(snapshot.latest_timestamp)
        self._put_text(
            frame_bgr,
            f"Latest session: {timestamp_text}",
            summary_x + 26,
            summary_y + 66,
            scale=0.55,
            color=self.MUTED,
            thickness=1,
            max_width=summary_w - 52,
        )

        cards_x = summary_x + 22
        cards_w = summary_w - 44
        gap = 12
        card_w = (cards_w - (gap * 3)) // 4
        card_h = 62
        row_one_y = summary_y + 90
        row_two_y = row_one_y + card_h + gap
        row_three_y = row_two_y + card_h + gap

        metrics = [
            ("Total Sessions", str(snapshot.total_sessions), self.PRIMARY),
            ("Meaningful", str(snapshot.meaningful_session_count), self.TEXT),
            (
                "Latest Reps",
                self._format_metric_value(snapshot.latest_rep_count),
                self.TEXT,
            ),
            (
                "Latest Bad",
                self._format_metric_value(snapshot.latest_bad_rep_count),
                self.ERROR if (snapshot.latest_bad_rep_count or 0) > 0 else self.TEXT,
            ),
            (
                "Bad Rep Rate",
                self._format_percentage(snapshot.latest_bad_rep_percentage),
                (
                    self.WARNING
                    if (snapshot.latest_bad_rep_percentage or 0.0) > 0
                    else self.TEXT
                ),
            ),
            ("Avg Knee", self._format_angle(snapshot.latest_avg_knee_angle), self.TEXT),
            ("Min Knee", self._format_angle(snapshot.latest_min_knee_angle), self.TEXT),
            (
                "Avg Ankle",
                self._format_angle(snapshot.latest_avg_ankle_angle),
                self.TEXT,
            ),
        ]

        for index, (label, value, color) in enumerate(metrics):
            col = index % 4
            row = index // 4
            self._draw_metric_tile(
                frame_bgr,
                cards_x + ((card_w + gap) * col),
                row_one_y if row == 0 else row_two_y,
                card_w,
                card_h,
                label,
                value,
                color,
                value_scale=0.68,
            )

        self._draw_metric_tile(
            frame_bgr,
            cards_x,
            row_three_y,
            card_w,
            54,
            "Avg Torso Lean",
            self._format_angle(snapshot.latest_avg_torso_angle),
            self.TEXT,
            value_scale=0.56,
        )
        self._draw_metric_tile(
            frame_bgr,
            cards_x + card_w + gap,
            row_three_y,
            (card_w * 3) + (gap * 2),
            54,
            "Most Common Issue",
            self._format_issue(snapshot.latest_most_common_issue),
            self.PRIMARY if not snapshot.latest_most_common_issue else self.WARNING,
            value_scale=0.58,
        )

        panel_gap = 18
        progress_x = margin
        progress_w = (frame_w - (margin * 2) - panel_gap) // 2
        report_x = progress_x + progress_w + panel_gap
        report_w = frame_w - report_x - margin

        self._draw_progress_panel(
            frame_bgr,
            progress_x,
            lower_y,
            progress_w,
            lower_h,
            snapshot,
        )
        self._draw_session_report_panel(
            frame_bgr,
            report_x,
            lower_y,
            report_w,
            lower_h,
            snapshot,
        )

    def draw_debug(self, frame_bgr, debug_info: dict) -> None:
        lines = [
            "Debug (D to toggle)",
            f"FPS: {debug_info.get('fps', 0.0):.1f}",
            f"Pose detected: {'yes' if debug_info.get('pose_detected') else 'no'}",
        ]

        knee_angle = debug_info.get("knee_angle")
        ankle_angle = debug_info.get("ankle_angle")
        torso_angle = debug_info.get("torso_angle")
        lines.append(
            "Knee angle: n/a" if knee_angle is None else f"Knee angle: {knee_angle:.1f}"
        )
        lines.append(
            "Ankle angle: n/a"
            if ankle_angle is None
            else f"Ankle angle: {ankle_angle:.1f}"
        )
        lines.append(
            "Torso angle: n/a"
            if torso_angle is None
            else f"Torso angle: {torso_angle:.1f}"
        )
        lines.extend(
            [
                f"down_knee_angle: {debug_info.get('down_knee_angle')}",
                f"up_knee_angle: {debug_info.get('up_knee_angle')}",
                f"rep_bottom_knee_angle: {debug_info.get('rep_bottom_knee_angle')}",
                f"shallow_knee_angle: {debug_info.get('shallow_knee_angle')}",
                f"ankle_control_angle: {debug_info.get('ankle_control_angle')}",
                f"torso_lean_angle: {debug_info.get('torso_lean_angle')}",
                f"down_hold_frames: {debug_info.get('down_hold_frames')}",
                f"ready_standing_frames: {debug_info.get('ready_standing_frames')}",
                f"min_rep_seconds: {debug_info.get('min_rep_seconds')}",
            ]
        )

        panel_x = 20
        panel_y = 244
        line_height = 25
        panel_w = 470
        panel_h = 24 + line_height * len(lines)
        self._draw_panel(
            frame_bgr,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            border_color=self.WARNING,
            alpha=0.84,
        )

        y = panel_y + 28
        for line in lines:
            self._put_text(
                frame_bgr,
                line,
                panel_x + 14,
                y,
                scale=0.5,
                color=self.TEXT,
                thickness=1,
                max_width=panel_w - 28,
            )
            y += line_height

    def _draw_progress_panel(self, frame_bgr, x, y, width, height, snapshot) -> None:
        self._draw_panel(
            frame_bgr,
            x,
            y,
            width,
            height,
            color=self.PANEL,
            border_color=self.BORDER,
            alpha=0.95,
        )
        self._put_text(
            frame_bgr,
            "Progress Comparison",
            x + 24,
            y + 34,
            scale=0.66,
            color=self.TEXT,
            thickness=1,
            max_width=width - 48,
        )
        self._put_text(
            frame_bgr,
            f"Previous: {self._format_session_timestamp(snapshot.previous_timestamp)}",
            x + 24,
            y + 62,
            scale=0.5,
            color=self.MUTED,
            thickness=1,
            max_width=width - 48,
        )

        card_gap = 10
        card_w = (width - 48 - (card_gap * 2)) // 3
        card_y = y + 92
        self._draw_metric_tile(
            frame_bgr,
            x + 24,
            card_y,
            card_w,
            68,
            "Reps",
            self._format_change(snapshot.rep_count_change),
            self._change_color(snapshot.rep_count_change, positive_is_good=True),
            label_scale=0.42,
            value_scale=0.64,
        )
        self._draw_metric_tile(
            frame_bgr,
            x + 24 + card_w + card_gap,
            card_y,
            card_w,
            68,
            "Bad Rate",
            self._format_percentage_point_change(snapshot.bad_rep_percentage_change),
            self._change_color(
                snapshot.bad_rep_percentage_change, positive_is_good=False
            ),
            label_scale=0.42,
            value_scale=0.52,
        )
        self._draw_metric_tile(
            frame_bgr,
            x + 24 + ((card_w + card_gap) * 2),
            card_y,
            card_w,
            68,
            "Avg Knee",
            self._format_angle_change(snapshot.avg_knee_angle_change),
            self.TEXT,
            label_scale=0.42,
            value_scale=0.52,
        )

        self._put_text(
            frame_bgr,
            f"Previous rep count: {self._format_metric_value(snapshot.previous_rep_count)}",
            x + 24,
            y + height - 24,
            scale=0.5,
            color=self.MUTED,
            thickness=1,
            max_width=width - 48,
        )

    def _draw_session_report_panel(
        self, frame_bgr, x, y, width, height, snapshot
    ) -> None:
        self._draw_panel(
            frame_bgr,
            x,
            y,
            width,
            height,
            color=self.PANEL,
            border_color=self.BORDER_ACTIVE,
            alpha=0.95,
        )
        cv2.line(
            frame_bgr, (x + 14, y + 18), (x + 14, y + height - 18), self.PRIMARY, 4
        )
        self._put_text(
            frame_bgr,
            "Session Report",
            x + 34,
            y + 34,
            scale=0.66,
            color=self.TEXT,
            thickness=1,
            max_width=width - 48,
        )
        item_y = y + 66
        gap = 42
        self._draw_report_item(
            frame_bgr,
            x + 34,
            item_y,
            width - 52,
            "Main concern",
            snapshot.main_concern or "N/A",
            self.TEXT,
        )
        self._draw_report_item(
            frame_bgr,
            x + 34,
            item_y + gap,
            width - 52,
            "Suggested improvement",
            snapshot.suggested_improvement or "N/A",
            self.MUTED,
        )
        self._draw_report_item(
            frame_bgr,
            x + 34,
            item_y + (gap * 2),
            width - 52,
            "Focus area",
            snapshot.focus_area or "N/A",
            self.PRIMARY,
        )

    def _draw_pose_points(self, frame_bgr, results) -> None:
        if not results or not getattr(results, "pose_landmarks", None):
            return
        if len(results.pose_landmarks) == 0:
            return

        landmarks = results.pose_landmarks[0]
        h, w = frame_bgr.shape[:2]
        for lm in landmarks:
            x = int(lm.x * w)
            y = int(lm.y * h)
            cv2.circle(frame_bgr, (x, y), 3, self.PRIMARY, -1)

    def _draw_session_panel(
        self,
        frame_bgr,
        squat_state,
        rep_counter=None,
        feedback_message: str | None = None,
        feedback_level: str = "info",
    ) -> None:
        panel_x = 24
        panel_y = 24
        panel_w = 408
        panel_h = 170
        pad = 16

        self._draw_panel(
            frame_bgr,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            color=self.LIVE_PANEL,
            border_color=self.LIVE_BORDER,
            alpha=0.86,
            radius=18,
        )

        state_text = squat_state.label.replace("_", " ").title()
        state_color = self.WARNING if "No Pose" in state_text else self.LIVE_BORDER
        self._put_text(
            frame_bgr,
            "Live Squat Session",
            panel_x + pad,
            panel_y + 26,
            scale=0.38,
            color=self.LIVE_MUTED,
            thickness=1,
            max_width=panel_w - (pad * 2),
        )
        self._put_text(
            frame_bgr,
            state_text,
            panel_x + pad,
            panel_y + 56,
            scale=0.66,
            color=state_color,
            thickness=2,
            max_width=panel_w - (pad * 2),
        )

        chip_y = panel_y + 70
        chip_w = 116
        chip_gap = 8
        self._draw_angle_chip(
            frame_bgr, panel_x + pad, chip_y, chip_w, "Knee", squat_state.knee_angle
        )
        self._draw_angle_chip(
            frame_bgr,
            panel_x + pad + chip_w + chip_gap,
            chip_y,
            chip_w,
            "Ankle",
            squat_state.ankle_angle,
        )
        self._draw_angle_chip(
            frame_bgr,
            panel_x + pad + ((chip_w + chip_gap) * 2),
            chip_y,
            chip_w,
            "Torso",
            squat_state.torso_angle,
        )

        if rep_counter is None:
            if feedback_message:
                self._draw_live_focus_text(
                    frame_bgr,
                    panel_x + pad,
                    panel_y + 146,
                    panel_w - (pad * 2),
                    feedback_message,
                    feedback_level,
                )
            return

        self._draw_compact_count(
            frame_bgr,
            panel_x + pad,
            panel_y + 104,
            96,
            "Reps",
            str(rep_counter.rep_count),
            self.LIVE_TEXT,
        )
        self._draw_compact_count(
            frame_bgr,
            panel_x + pad + 106,
            panel_y + 104,
            96,
            "Bad",
            str(rep_counter.bad_rep_count),
            self.ERROR if rep_counter.bad_rep_count else self.LIVE_TEXT,
        )

        if feedback_message:
            self._draw_live_focus_text(
                frame_bgr,
                panel_x + pad,
                panel_y + 160,
                panel_w - (pad * 2),
                feedback_message,
                feedback_level,
            )
        else:
            last_text = self._format_result(rep_counter.last_rep_result)
            self._put_text(
                frame_bgr,
                f"Last rep: {last_text}",
                panel_x + pad,
                panel_y + 160,
                scale=0.36,
                color=self.LIVE_MUTED,
                thickness=1,
                max_width=panel_w - (pad * 2),
            )

    def _draw_compact_count(self, frame_bgr, x, y, width, label, value, color) -> None:
        self._draw_panel(
            frame_bgr,
            x,
            y,
            width,
            38,
            color=self.LIVE_CARD,
            border_color=(78, 94, 98),
            alpha=0.9,
            radius=10,
        )
        self._put_text(frame_bgr, label, x + 12, y + 16, 0.34, self.LIVE_MUTED)
        self._put_text(frame_bgr, value, x + 12, y + 34, 0.5, color, 2)

    def _draw_angle_chip(self, frame_bgr, x, y, width, label, value) -> None:
        self._draw_panel(
            frame_bgr,
            x,
            y,
            width,
            24,
            color=self.LIVE_CARD,
            border_color=(78, 94, 98),
            alpha=0.88,
            radius=12,
        )
        display = "n/a" if value is None else f"{value:.0f}"
        self._put_text(
            frame_bgr,
            f"{label} {display}",
            x + 10,
            y + 17,
            0.32,
            self.LIVE_TEXT,
            max_width=width - 20,
        )

    def _draw_live_focus_text(
        self,
        frame_bgr,
        x: int,
        y: int,
        width: int,
        message: str,
        feedback_level: str,
    ) -> None:
        colors = {
            "ok": self.LIVE_BORDER,
            "bad": self.ERROR,
            "warning": self.WARNING,
            "info": self.LIVE_TEXT,
        }
        color = colors.get(feedback_level, self.LIVE_TEXT)
        self._put_text(
            frame_bgr,
            message,
            x,
            y,
            0.36,
            color,
            thickness=1,
            max_width=width,
        )

    def _draw_metric_tile(
        self,
        frame_bgr,
        x: int,
        y: int,
        width: int,
        height: int,
        label: str,
        value: str,
        value_color: tuple[int, int, int],
        label_scale: float = 0.46,
        value_scale: float | None = None,
    ) -> None:
        label_y = y + 22
        value_y = y + height - 14
        if value_scale is None:
            value_scale = 0.7 if height < 70 else 0.82

        self._draw_panel(
            frame_bgr,
            x,
            y,
            width,
            height,
            color=self.PANEL_ALT,
            border_color=self.BORDER,
            alpha=0.94,
        )
        self._put_text(
            frame_bgr,
            label,
            x + 14,
            label_y,
            scale=label_scale,
            color=self.MUTED,
            thickness=1,
            max_width=width - 28,
        )
        self._put_text(
            frame_bgr,
            value,
            x + 14,
            value_y,
            scale=value_scale,
            color=value_color,
            thickness=1,
            max_width=width - 28,
        )

    def _draw_report_item(
        self,
        frame_bgr,
        x: int,
        y: int,
        width: int,
        label: str,
        value: str,
        value_color: tuple[int, int, int],
    ) -> None:
        self._put_text(frame_bgr, label, x, y, 0.44, self.MUTED, max_width=width)
        self._put_text(
            frame_bgr,
            value,
            x,
            y + 24,
            scale=0.54,
            color=value_color,
            thickness=1,
            max_width=width,
        )

    def _draw_feedback(
        self, frame_bgr, message: str, feedback_level: str = "info"
    ) -> None:
        colors = {
            "ok": self.PRIMARY,
            "bad": self.ERROR,
            "warning": self.WARNING,
            "info": self.TEXT,
        }
        color = colors.get(feedback_level, colors["info"])
        scale = 0.72
        thickness = 1
        _, frame_w = frame_bgr.shape[:2]
        max_panel_w = min(430, max(260, frame_w - 520))
        display_text = self._fit_text(message, max_panel_w - 36, scale, thickness)
        text_w = self._text_width(display_text, scale, thickness)
        text_h = self._text_height(display_text, scale, thickness)
        pad_x = 18
        pad_y = 14
        panel_w = max(250, text_w + (pad_x * 2))
        panel_h = text_h + (pad_y * 2)
        panel_x = frame_w - panel_w - 24
        panel_y = 24

        self._draw_panel(
            frame_bgr,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            color=self.BG_SOFT,
            border_color=color,
            alpha=0.84,
        )
        self._put_text(
            frame_bgr,
            display_text,
            panel_x + pad_x,
            panel_y + pad_y + text_h,
            scale=scale,
            color=color,
            thickness=thickness,
            max_width=panel_w - (pad_x * 2),
        )

    def _draw_pill(
        self,
        frame_bgr,
        x: int,
        y: int,
        text: str,
        text_color: tuple[int, int, int],
        fill_color: tuple[int, int, int],
    ) -> None:
        scale = 0.42
        text_w = self._text_width(text, scale, 1)
        width = text_w + 28
        height = 28
        self._draw_panel(
            frame_bgr,
            x,
            y,
            width,
            height,
            color=fill_color,
            border_color=self.PRIMARY_SOFT,
            alpha=0.92,
            radius=14,
        )
        self._put_text(
            frame_bgr, text, x + 14, y + 20, scale, text_color, max_width=width - 28
        )

    def _draw_info_card(
        self,
        frame_bgr,
        x: int,
        y: int,
        width: int,
        label: str,
        value: str,
    ) -> None:
        self._draw_panel(
            frame_bgr,
            x,
            y,
            width,
            82,
            color=self.PANEL_ALT,
            border_color=self.BORDER,
            alpha=0.9,
            radius=16,
        )
        self._put_text(frame_bgr, label.upper(), x + 18, y + 28, 0.36, self.MUTED)
        self._put_text(
            frame_bgr, value, x + 18, y + 58, 0.5, self.TEXT, max_width=width - 36
        )

    def _draw_action_card(
        self,
        frame_bgr,
        x: int,
        y: int,
        width: int,
        height: int,
        key: str,
        title: str,
        subtitle: str,
    ) -> None:
        self._draw_panel(
            frame_bgr,
            x,
            y,
            width,
            height,
            color=self.PANEL_ALT,
            border_color=self.BORDER,
            alpha=0.94,
            radius=18,
        )
        self._draw_panel(
            frame_bgr,
            x + 18,
            y + 20,
            54 if key != "Esc" else 70,
            44,
            color=self.SELECTED,
            border_color=self.BORDER_ACTIVE,
            alpha=0.95,
            radius=12,
        )
        key_box_w = 54 if key != "Esc" else 70
        self._put_text_centered(
            frame_bgr,
            key,
            x + 18,
            y + 20,
            key_box_w,
            44,
            0.46,
            self.PRIMARY,
            2,
        )
        text_x = x + 92 if key != "Esc" else x + 108
        self._put_text(
            frame_bgr,
            title,
            text_x,
            y + 38,
            0.58,
            self.TEXT,
            2,
            max_width=width - (text_x - x) - 24,
        )
        self._put_text(
            frame_bgr,
            subtitle,
            text_x,
            y + 62,
            0.4,
            self.MUTED,
            max_width=width - (text_x - x) - 24,
        )

    def _draw_menu_row(
        self,
        frame_bgr,
        x: int,
        y: int,
        width: int,
        key: str,
        title: str,
        subtitle: str = "",
    ) -> None:
        row_h = 54
        key_scale = 0.58
        key_thickness = 1
        key_width = self._text_width(key, key_scale, key_thickness)
        key_box_w = max(42, key_width + 22)
        key_box_x = x + 18

        self._draw_panel(
            frame_bgr,
            x,
            y - 34,
            width,
            row_h,
            color=self.PANEL_ALT,
            border_color=self.BORDER,
            alpha=0.94,
        )
        cv2.rectangle(
            frame_bgr,
            (key_box_x, y - 24),
            (key_box_x + key_box_w, y + 12),
            self.SELECTED,
            -1,
        )
        cv2.rectangle(
            frame_bgr,
            (key_box_x, y - 24),
            (key_box_x + key_box_w, y + 12),
            self.BORDER_ACTIVE,
            1,
        )
        self._put_text_centered(
            frame_bgr,
            key,
            key_box_x,
            y - 24,
            key_box_w,
            36,
            key_scale,
            self.PRIMARY,
            key_thickness,
        )
        self._put_text(
            frame_bgr,
            title,
            key_box_x + key_box_w + 22,
            y - 4,
            scale=0.62,
            color=self.TEXT,
            thickness=1,
            max_width=width - key_box_w - 58,
        )
        if subtitle:
            self._put_text(
                frame_bgr,
                subtitle,
                key_box_x + key_box_w + 22,
                y + 18,
                scale=0.42,
                color=self.MUTED,
                thickness=1,
                max_width=width - key_box_w - 58,
            )

    def _draw_screen_header(
        self, frame_bgr, margin: int, title: str, hint: str
    ) -> None:
        self._put_text(
            frame_bgr,
            title,
            margin,
            64,
            scale=0.98,
            color=self.TEXT,
            thickness=2,
            max_width=900,
        )
        cv2.line(frame_bgr, (margin, 78), (margin + 76, 78), self.PRIMARY, 4)
        self._put_text(
            frame_bgr,
            hint,
            margin + 2,
            102,
            scale=0.44,
            color=self.MUTED,
            thickness=1,
            max_width=1100,
        )

    def _draw_empty_state(self, frame_bgr, x, y, width, title, subtitle) -> None:
        self._put_text(
            frame_bgr,
            title,
            x + 28,
            y + 92,
            scale=0.72,
            color=self.TEXT,
            thickness=1,
            max_width=width - 56,
        )
        self._put_text(
            frame_bgr,
            subtitle,
            x + 28,
            y + 124,
            scale=0.5,
            color=self.MUTED,
            thickness=1,
            max_width=width - 56,
        )

    def _fill_background(self, frame_bgr) -> None:
        frame_h, frame_w = frame_bgr.shape[:2]
        top = np.array(self.BG_SOFT, dtype=np.float32)
        bottom = np.array(self.BG, dtype=np.float32)
        for row in range(frame_h):
            blend = row / max(1, frame_h - 1)
            frame_bgr[row, :] = (top * (1 - blend) + bottom * blend).astype(np.uint8)

        texture = frame_bgr.copy()
        for x in range(-frame_h, frame_w, 92):
            cv2.line(texture, (x, frame_h), (x + frame_h, 0), (211, 224, 218), 1)
        cv2.addWeighted(texture, 0.24, frame_bgr, 0.76, 0, frame_bgr)

        cv2.rectangle(frame_bgr, (0, 0), (frame_w, 104), (221, 234, 228), -1)
        cv2.line(frame_bgr, (0, 104), (frame_w, 104), (175, 198, 187), 1)
        cv2.line(frame_bgr, (0, 105), (frame_w, 105), self.PRIMARY, 2)

        glow = frame_bgr.copy()
        cv2.circle(glow, (frame_w - 120, 78), 210, (188, 222, 204), -1)
        cv2.circle(glow, (92, frame_h - 76), 180, (217, 226, 229), -1)
        cv2.addWeighted(glow, 0.32, frame_bgr, 0.68, 0, frame_bgr)
        cv2.rectangle(
            frame_bgr, (0, frame_h - 6), (frame_w, frame_h), (184, 215, 199), -1
        )

    def _draw_panel(
        self,
        frame_bgr,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int] = PANEL,
        border_color: tuple[int, int, int] = BORDER,
        alpha: float = 0.88,
        radius: int = 14,
    ) -> None:
        overlay = frame_bgr.copy()
        self._draw_rounded_rect(overlay, x, y, width, height, radius, color, -1)
        cv2.addWeighted(overlay, alpha, frame_bgr, 1 - alpha, 0, frame_bgr)
        self._draw_rounded_rect(frame_bgr, x, y, width, height, radius, border_color, 1)

    @staticmethod
    def _draw_rounded_rect(
        frame_bgr,
        x: int,
        y: int,
        width: int,
        height: int,
        radius: int,
        color: tuple[int, int, int],
        thickness: int,
    ) -> None:
        radius = max(0, min(radius, width // 2, height // 2))
        x2 = x + width
        y2 = y + height

        if radius == 0:
            cv2.rectangle(frame_bgr, (x, y), (x2, y2), color, thickness)
            return

        if thickness < 0:
            cv2.rectangle(frame_bgr, (x + radius, y), (x2 - radius, y2), color, -1)
            cv2.rectangle(frame_bgr, (x, y + radius), (x2, y2 - radius), color, -1)
            cv2.circle(frame_bgr, (x + radius, y + radius), radius, color, -1)
            cv2.circle(frame_bgr, (x2 - radius, y + radius), radius, color, -1)
            cv2.circle(frame_bgr, (x + radius, y2 - radius), radius, color, -1)
            cv2.circle(frame_bgr, (x2 - radius, y2 - radius), radius, color, -1)
            return

        cv2.line(
            frame_bgr, (x + radius, y), (x2 - radius, y), color, thickness, cv2.LINE_AA
        )
        cv2.line(
            frame_bgr,
            (x + radius, y2),
            (x2 - radius, y2),
            color,
            thickness,
            cv2.LINE_AA,
        )
        cv2.line(
            frame_bgr, (x, y + radius), (x, y2 - radius), color, thickness, cv2.LINE_AA
        )
        cv2.line(
            frame_bgr,
            (x2, y + radius),
            (x2, y2 - radius),
            color,
            thickness,
            cv2.LINE_AA,
        )
        cv2.ellipse(
            frame_bgr,
            (x + radius, y + radius),
            (radius, radius),
            180,
            0,
            90,
            color,
            thickness,
            cv2.LINE_AA,
        )
        cv2.ellipse(
            frame_bgr,
            (x2 - radius, y + radius),
            (radius, radius),
            270,
            0,
            90,
            color,
            thickness,
            cv2.LINE_AA,
        )
        cv2.ellipse(
            frame_bgr,
            (x2 - radius, y2 - radius),
            (radius, radius),
            0,
            0,
            90,
            color,
            thickness,
            cv2.LINE_AA,
        )
        cv2.ellipse(
            frame_bgr,
            (x + radius, y2 - radius),
            (radius, radius),
            90,
            0,
            90,
            color,
            thickness,
            cv2.LINE_AA,
        )

    def _put_text(
        self,
        frame_bgr,
        text: str,
        x: int,
        y: int,
        scale: float,
        color: tuple[int, int, int],
        thickness: int = 1,
        max_width: int | None = None,
    ) -> None:
        display_text = text
        if max_width is not None:
            display_text = self._fit_text(text, max_width, scale, thickness)

        font = self._load_font(self._font_size(scale), thickness > 1)
        bbox = font.getbbox(display_text)
        draw_x = int(x) - bbox[0]
        draw_y = int(y) - bbox[3]
        self._draw_text_at(frame_bgr, display_text, draw_x, draw_y, font, color)

    def _put_text_centered(
        self,
        frame_bgr,
        text: str,
        x: int,
        y: int,
        width: int,
        height: int,
        scale: float,
        color: tuple[int, int, int],
        thickness: int = 1,
    ) -> None:
        font = self._load_font(self._font_size(scale), thickness > 1)
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw_x = int(x + ((width - text_w) / 2) - bbox[0])
        draw_y = int(y + ((height - text_h) / 2) - bbox[1])
        self._draw_text_at(frame_bgr, text, draw_x, draw_y, font, color)

    def _draw_text_at(
        self,
        frame_bgr,
        text: str,
        draw_x: int,
        draw_y: int,
        font,
        color: tuple[int, int, int],
    ) -> None:
        bbox = font.getbbox(text)
        frame_h, frame_w = frame_bgr.shape[:2]
        left = max(0, draw_x + bbox[0] - 3)
        top = max(0, draw_y + bbox[1] - 3)
        right = min(frame_w, draw_x + bbox[2] + 4)
        bottom = min(frame_h, draw_y + bbox[3] + 5)
        if right <= left or bottom <= top:
            return

        roi = frame_bgr[top:bottom, left:right]
        image = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(image)
        draw.text(
            (draw_x - left, draw_y - top),
            text,
            font=font,
            fill=self._bgr_to_rgb(color),
        )
        frame_bgr[top:bottom, left:right] = cv2.cvtColor(
            np.array(image), cv2.COLOR_RGB2BGR
        )

    def _fit_text(self, text: str, max_width: int, scale: float, thickness: int) -> str:
        if max_width <= 0:
            return "..."
        if self._text_width(text, scale, thickness) <= max_width:
            return text

        ellipsis = "..."
        low = 0
        high = len(text)
        while low < high:
            mid = (low + high + 1) // 2
            candidate = text[:mid].rstrip() + ellipsis
            if self._text_width(candidate, scale, thickness) <= max_width:
                low = mid
            else:
                high = mid - 1
        return text[:low].rstrip() + ellipsis

    def _text_width(self, text: str, scale: float, thickness: int) -> int:
        font = self._load_font(self._font_size(scale), thickness > 1)
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

    def _text_height(self, text: str, scale: float, thickness: int) -> int:
        font = self._load_font(self._font_size(scale), thickness > 1)
        bbox = font.getbbox(text)
        return bbox[3] - bbox[1]

    @staticmethod
    def _font_size(scale: float) -> int:
        return max(10, int(round(scale * 34)))

    @staticmethod
    @lru_cache(maxsize=64)
    def _load_font(size: int, bold: bool = False):
        preferred = OverlayRenderer.FONT_BOLD if bold else OverlayRenderer.FONT_REGULAR
        fallbacks = [
            preferred,
            OverlayRenderer.FONT_REGULAR,
            Path(r"C:\Windows\Fonts\arial.ttf"),
        ]
        for font_path in fallbacks:
            if font_path.exists():
                return ImageFont.truetype(str(font_path), size=size)
        return ImageFont.load_default()

    @staticmethod
    def _bgr_to_rgb(color: tuple[int, int, int]) -> tuple[int, int, int]:
        return (color[2], color[1], color[0])

    @staticmethod
    def _format_result(value: str) -> str:
        if not value or value == "none":
            return "none"
        return value.replace("_", " ")

    @staticmethod
    def _format_metric_value(value) -> str:
        if value is None:
            return "N/A"
        return str(value)

    @staticmethod
    def _format_percentage(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.1f}%"

    @staticmethod
    def _format_change(value: int | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:+d}"

    @staticmethod
    def _format_percentage_point_change(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:+.1f} pts"

    @staticmethod
    def _format_angle_metric(label: str, value: float | None) -> str:
        if value is None:
            return f"{label}: n/a"
        return f"{label}: {value:.1f}"

    @staticmethod
    def _format_angle(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.1f} deg"

    @staticmethod
    def _format_angle_change(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:+.1f} deg"

    @staticmethod
    def _format_issue(value: str | None) -> str:
        if not value:
            return "none"
        return value.replace("_", " ")

    def _change_color(
        self, value: int | float | None, *, positive_is_good: bool
    ) -> tuple[int, int, int]:
        if value is None or value == 0:
            return self.TEXT
        if positive_is_good:
            return self.PRIMARY if value > 0 else self.WARNING
        return self.PRIMARY if value < 0 else self.ERROR

    @staticmethod
    def _format_session_timestamp(value: str | None) -> str:
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
