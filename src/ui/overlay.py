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
    BG = (239, 247, 242)
    BG_SOFT = (250, 253, 250)
    PANEL = (255, 255, 255)
    PANEL_ALT = (248, 251, 249)
    PANEL_STRONG = (229, 243, 234)
    SELECTED = (212, 236, 219)
    BORDER = (193, 211, 198)
    BORDER_ACTIVE = (74, 142, 86)

    PRIMARY = (45, 119, 67)
    PRIMARY_SOFT = (218, 239, 224)
    WARNING = (0, 143, 204)
    ERROR = (76, 86, 205)
    INFO = (196, 127, 66)
    TEXT = (28, 47, 38)
    MUTED = (88, 108, 99)
    MUTED_DARK = (138, 152, 145)
    LIVE_PANEL = (36, 47, 49)
    LIVE_CARD = (48, 60, 62)
    LIVE_BORDER = (102, 218, 150)
    LIVE_TEXT = (244, 248, 246)
    LIVE_MUTED = (178, 194, 190)
    SHADOW = (0, 0, 0)

    THEMES = {
        "light": {
            "BG": BG,
            "BG_SOFT": BG_SOFT,
            "PANEL": PANEL,
            "PANEL_ALT": PANEL_ALT,
            "PANEL_STRONG": PANEL_STRONG,
            "SELECTED": SELECTED,
            "BORDER": BORDER,
            "BORDER_ACTIVE": BORDER_ACTIVE,
            "PRIMARY": PRIMARY,
            "PRIMARY_SOFT": PRIMARY_SOFT,
            "WARNING": WARNING,
            "ERROR": ERROR,
            "INFO": INFO,
            "TEXT": TEXT,
            "MUTED": MUTED,
            "MUTED_DARK": MUTED_DARK,
            "LIVE_PANEL": LIVE_PANEL,
            "LIVE_CARD": LIVE_CARD,
            "LIVE_BORDER": LIVE_BORDER,
            "LIVE_TEXT": LIVE_TEXT,
            "LIVE_MUTED": LIVE_MUTED,
        },
        "dark": {
            "BG": (39, 24, 17),
            "BG_SOFT": (47, 35, 24),
            "PANEL": (53, 45, 36),
            "PANEL_ALT": (63, 54, 43),
            "PANEL_STRONG": (74, 64, 50),
            "SELECTED": (82, 91, 33),
            "BORDER": (82, 67, 51),
            "BORDER_ACTIVE": (150, 222, 104),
            "PRIMARY": (155, 226, 100),
            "PRIMARY_SOFT": (69, 90, 30),
            "WARNING": (66, 185, 245),
            "ERROR": (113, 113, 248),
            "INFO": (250, 165, 96),
            "TEXT": (252, 250, 248),
            "MUTED": (184, 163, 148),
            "MUTED_DARK": (123, 120, 108),
            "LIVE_PANEL": (47, 35, 24),
            "LIVE_CARD": (53, 45, 36),
            "LIVE_BORDER": (150, 222, 104),
            "LIVE_TEXT": (252, 250, 248),
            "LIVE_MUTED": (184, 163, 148),
        },
    }

    def __init__(self, theme: str = "light") -> None:
        self.theme = "light"
        self.set_theme(theme)

    def set_theme(self, theme: str) -> None:
        selected_theme = theme if theme in self.THEMES else "light"
        for key, value in self.THEMES[selected_theme].items():
            setattr(self, key, value)
        self.theme = selected_theme

    def draw(
        self,
        frame_bgr,
        results,
        squat_state,
        rep_counter=None,
        feedback_message: str | None = None,
        feedback_level: str = "info",
        calibration_profile=None,
    ) -> None:
        self._draw_pose_points(frame_bgr, results)
        self._draw_session_panel(
            frame_bgr,
            squat_state,
            rep_counter,
            feedback_message,
            feedback_level,
            calibration_profile,
        )
        if feedback_message and (
            feedback_level in {"ok", "bad"}
            or feedback_message.startswith("Rep logged")
        ):
            self._draw_feedback(frame_bgr, feedback_message, feedback_level)

    def draw_dashboard(
        self,
        frame_bgr,
        calibration_profile=None,
        settings=None,
        notice_message: str | None = None,
        camera_options=None,
    ) -> None:
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
            shell_y + 42,
            "Desktop squat coach",
            self.PRIMARY,
            self.SELECTED,
        )

        self._put_text(
            frame_bgr,
            "GymGuardian",
            shell_x + 58,
            shell_y + 150,
            scale=1.38,
            color=self.PRIMARY,
            thickness=2,
            max_width=390,
        )
        self._put_text(
            frame_bgr,
            "Real-time form feedback, local session evidence, and progress analytics.",
            shell_x + 62,
            shell_y + 198,
            scale=0.62,
            color=self.MUTED,
            thickness=1,
            max_width=shell_w - 124,
        )

        camera_index = getattr(settings, "camera_index", 0)
        camera_label = self._format_camera_display(
            camera_index,
            camera_options,
            include_index=True,
        )
        insight_w = 190
        insight_gap = 14
        insight_x = shell_x + shell_w - (insight_w * 3) - (insight_gap * 2) - 48
        insight_y = shell_y + 58
        self._draw_info_card(
            frame_bgr, insight_x, insight_y, insight_w, "Scope", "Squat analysis only"
        )
        self._draw_info_card(
            frame_bgr,
            insight_x + insight_w + insight_gap,
            insight_y,
            insight_w,
            "Camera",
            camera_label,
        )
        self._draw_info_card(
            frame_bgr,
            insight_x + ((insight_w + insight_gap) * 2),
            insight_y,
            insight_w,
            "Calibration",
            "Adaptive thresholds" if calibration_profile else "Default thresholds",
        )

        options = [
            ("S", "Start squat session", "Open webcam and begin form tracking"),
            ("V", "Analyse local video", "Process newest file in input_videos"),
            ("C", "Calibrate squat depth", "Personalise thresholds with 2-3 squats"),
            ("A", "Open analytics dashboard", "View progress and recommendations"),
            ("B", "Browse saved sessions", "Review videos and session files"),
            ("G", "Open settings", "Theme, calibration, and browser display"),
        ]

        card_gap = 10
        cards_x = shell_x + 58
        cards_y = shell_y + 248
        card_w = (shell_w - 116 - card_gap) // 2
        card_h = 64
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

        if notice_message:
            self._put_text(
                frame_bgr,
                notice_message,
                shell_x + 62,
                shell_y + 224,
                scale=0.42,
                color=self.WARNING,
                thickness=1,
                max_width=shell_w - 124,
            )

        self._put_text(
            frame_bgr,
            "Keyboard desktop prototype. V analyses videos. K switches camera. Esc quits/returns.",
            shell_x + 62,
            shell_y + shell_h - 34,
            scale=0.47,
            color=self.MUTED,
            thickness=1,
            max_width=shell_w - 124,
        )

    def draw_browser(
        self,
        frame_bgr,
        sessions,
        selected_index: int,
        hide_incomplete_sessions: bool = False,
    ) -> None:
        self._fill_background(frame_bgr)
        frame_h, frame_w = frame_bgr.shape[:2]
        margin = 34

        browser_hint = (
            "Up/Down select  |  P play video  |  O open folder  |  H show invalid tests  |  Esc dashboard"
            if hide_incomplete_sessions
            else "Up/Down select  |  P play video  |  O open folder  |  H hide invalid tests  |  Esc dashboard"
        )
        self._draw_screen_header(
            frame_bgr,
            margin,
            "Session Browser",
            browser_hint,
        )

        list_x = margin
        list_y = 126
        list_w = frame_w - (margin * 2)
        list_h = frame_h - list_y - margin
        metric_w = 70
        if hide_incomplete_sessions:
            fps_w = 90
            knee_w = 120
            fps_x = list_x + list_w - 150
            knee_x = list_x + list_w - 300
            bad_x = list_x + list_w - 420
            reps_x = list_x + list_w - 540
            status_x = status_w = None
        else:
            status_x = list_x + list_w - 196
            status_w = 150
            bad_x = list_x + list_w - 318
            reps_x = list_x + list_w - 440
            knee_x = knee_w = fps_x = fps_w = None
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
                (
                    "No valid sessions shown"
                    if hide_incomplete_sessions
                    else "No saved sessions found"
                ),
                (
                    "Press H to show invalid tests too."
                    if hide_incomplete_sessions
                    else "Complete a workout session to populate this browser."
                ),
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
        if hide_incomplete_sessions:
            self._put_text_centered(
                frame_bgr,
                "Avg Knee",
                knee_x,
                header_y - 22,
                knee_w,
                24,
                0.52,
                self.MUTED,
            )
            self._put_text_centered(
                frame_bgr,
                "Avg FPS",
                fps_x,
                header_y - 22,
                fps_w,
                24,
                0.52,
                self.MUTED,
            )
        else:
            self._put_text_centered(
                frame_bgr,
                "Status",
                status_x,
                header_y - 22,
                status_w,
                24,
                0.52,
                self.MUTED,
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
            avg_knee = self._format_angle(getattr(item, "avg_knee_angle", None))
            avg_fps = self._format_fps(getattr(item, "avg_fps", None))
            is_valid = bool(
                getattr(item, "valid_session", item.rep_count not in (None, 0))
            )
            status_text = "Complete" if is_valid else "Incomplete"
            display_name = str(item.folder_name).strip()
            selected_fill = (82, 91, 33)
            selected_border = (150, 222, 104)
            selected_text = (252, 250, 248)
            complete_status_fill = (43, 58, 24)
            complete_status_border = (73, 110, 44)
            complete_status_text = (155, 226, 100)
            incomplete_status_fill = (29, 51, 60)
            incomplete_status_border = (38, 90, 103)
            incomplete_status_text = (66, 185, 245)

            if self.theme == "dark":
                row_color = (
                    selected_fill
                    if selected
                    else (96, 90, 61)
                    if is_valid
                    else self.PANEL_ALT
                )
                border_color = (
                    selected_border
                    if selected
                    else (120, 140, 77)
                    if is_valid
                    else self.BORDER
                )
                primary_color = selected_text if selected or is_valid else self.MUTED
                metric_color = selected_text if selected or is_valid else self.MUTED
            else:
                row_color = (
                    selected_fill
                    if selected
                    else (235, 246, 238)
                    if is_valid
                    else (246, 249, 247)
                )
                border_color = (
                    selected_border
                    if selected
                    else (142, 186, 151)
                    if is_valid
                    else self.BORDER
                )
                primary_color = selected_text if selected else self.TEXT if is_valid else self.MUTED
                metric_color = selected_text if selected else self.TEXT if is_valid else self.MUTED

            selected_rail_color = selected_border
            status_fill = complete_status_fill if is_valid else incomplete_status_fill
            status_border = complete_status_border if is_valid else incomplete_status_border
            status_color = complete_status_text if is_valid else incomplete_status_text

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
                    selected_rail_color,
                    5,
                )

            self._put_text(
                frame_bgr,
                display_name,
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
            if hide_incomplete_sessions:
                self._put_text_centered(
                    frame_bgr,
                    avg_knee,
                    knee_x,
                    row_y - 28,
                    knee_w,
                    row_h,
                    0.56,
                    metric_color,
                )
                self._put_text_centered(
                    frame_bgr,
                    avg_fps,
                    fps_x,
                    row_y - 28,
                    fps_w,
                    row_h,
                    0.56,
                    metric_color,
                )
            else:
                self._draw_panel(
                    frame_bgr,
                    status_x,
                    row_y - 25,
                    status_w,
                    28,
                    color=status_fill,
                    border_color=status_border,
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

    def draw_analytics(self, frame_bgr, snapshot, calibration_profile=None) -> None:
        self._fill_background(frame_bgr)
        frame_h, frame_w = frame_bgr.shape[:2]
        margin = 30

        self._draw_screen_header(
            frame_bgr,
            margin,
            "Analytics Dashboard",
            "R refresh  |  E export report  |  Esc dashboard",
        )

        summary_x = margin
        summary_y = 118
        summary_w = frame_w - (margin * 2)
        summary_h = 310
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
        self._draw_calibration_badge(
            frame_bgr,
            summary_x + summary_w - 242,
            summary_y + 18,
            216,
            32,
            calibration_profile,
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
        card_h = 64
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
                label_scale=0.42,
                value_scale=0.58,
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
            label_scale=0.4,
            value_scale=0.48,
        )
        self._draw_metric_tile(
            frame_bgr,
            cards_x + card_w + gap,
            row_three_y,
            card_w,
            54,
            "Avg FPS",
            self._format_fps(snapshot.latest_avg_fps),
            self.INFO if snapshot.latest_avg_fps is not None else self.TEXT,
            label_scale=0.4,
            value_scale=0.48,
        )
        self._draw_metric_tile(
            frame_bgr,
            cards_x + ((card_w + gap) * 2),
            row_three_y,
            (card_w * 2) + gap,
            54,
            "Most Common Issue",
            self._format_issue(snapshot.latest_most_common_issue),
            self.PRIMARY if not snapshot.latest_most_common_issue else self.WARNING,
            label_scale=0.4,
            value_scale=0.5,
        )

        panel_gap = 18
        trend_x = margin
        trend_w = int((frame_w - (margin * 2) - panel_gap) * 0.58)
        side_x = trend_x + trend_w + panel_gap
        side_w = frame_w - side_x - margin
        side_gap = 14
        progress_h = max(118, (lower_h - side_gap) // 2)
        report_h = lower_h - progress_h - side_gap

        self._draw_trends_panel(
            frame_bgr,
            trend_x,
            lower_y,
            trend_w,
            lower_h,
            snapshot,
        )
        self._draw_progress_panel(
            frame_bgr,
            side_x,
            lower_y,
            side_w,
            progress_h,
            snapshot,
        )
        self._draw_session_report_panel(
            frame_bgr,
            side_x,
            lower_y + progress_h + side_gap,
            side_w,
            report_h,
            snapshot,
        )

    def draw_calibration(self, frame_bgr, results, squat_state, status: dict) -> None:
        if results is not None:
            self._draw_pose_points(frame_bgr, results)
        elif frame_bgr.mean() < 5:
            self._fill_background(frame_bgr)

        frame_h, frame_w = frame_bgr.shape[:2]
        panel_w = min(620, frame_w - 56)
        panel_h = 330
        panel_x = 28
        panel_y = 30
        phase = status.get("phase", "collecting")
        profile = status.get("profile")
        elapsed = float(status.get("elapsed", 0.0))
        duration = float(status.get("duration", 1.0))
        progress = min(1.0, elapsed / max(1.0, duration))

        self._draw_panel(
            frame_bgr,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            color=self.LIVE_PANEL,
            border_color=self.LIVE_BORDER,
            alpha=0.88,
            radius=20,
        )

        self._put_text(
            frame_bgr,
            "Squat Depth Calibration",
            panel_x + 24,
            panel_y + 42,
            0.72,
            self.LIVE_TEXT,
            2,
            max_width=panel_w - 48,
        )
        self._put_text(
            frame_bgr,
            "Perform 2-3 normal squats. Keep your lower body visible.",
            panel_x + 24,
            panel_y + 72,
            0.42,
            self.LIVE_MUTED,
            max_width=panel_w - 48,
        )

        bar_x = panel_x + 24
        bar_y = panel_y + 96
        bar_w = panel_w - 48
        self._draw_panel(
            frame_bgr,
            bar_x,
            bar_y,
            bar_w,
            16,
            color=self.LIVE_CARD,
            border_color=(78, 94, 98),
            alpha=0.88,
            radius=8,
        )
        fill_w = int(bar_w * progress) if phase == "collecting" else bar_w
        if fill_w > 0:
            self._draw_rounded_rect(
                frame_bgr,
                bar_x,
                bar_y,
                fill_w,
                16,
                8,
                self.LIVE_BORDER if phase == "saved" else self.WARNING,
                -1,
            )

        sample_text = f"Valid knee-angle samples: {status.get('sample_count', 0)}"
        current_angle = "Current knee: N/A"
        if squat_state is not None and squat_state.knee_angle is not None:
            current_angle = f"Current knee: {squat_state.knee_angle:.1f} deg"
        self._put_text(frame_bgr, sample_text, panel_x + 24, panel_y + 142, 0.46, self.LIVE_TEXT)
        self._put_text(frame_bgr, current_angle, panel_x + 310, panel_y + 142, 0.46, self.LIVE_TEXT)

        phase_label = {
            "collecting": "Collecting movement range",
            "saved": "Calibration saved",
            "failed": "Calibration needs retry",
            "reset": "Calibration reset",
            "error": "Calibration unavailable",
        }.get(phase, phase.title())
        phase_color = self.LIVE_BORDER if phase == "saved" else self.WARNING
        if phase in ("failed", "error"):
            phase_color = self.ERROR
        self._put_text(frame_bgr, phase_label, panel_x + 24, panel_y + 176, 0.56, phase_color, 2)
        self._put_text(
            frame_bgr,
            status.get("message", ""),
            panel_x + 24,
            panel_y + 204,
            0.4,
            self.LIVE_MUTED,
            max_width=panel_w - 48,
        )

        values_y = panel_y + 238
        if profile is not None:
            values = [
                ("Standing", profile.standing_knee_angle),
                ("Lowest", profile.lowest_knee_angle),
                ("Down", profile.calibrated_down_angle),
                ("Shallow", profile.calibrated_shallow_angle),
            ]
            card_w = (panel_w - 48 - 24) // 4
            for index, (label, value) in enumerate(values):
                x = panel_x + 24 + (card_w + 8) * index
                self._draw_panel(
                    frame_bgr,
                    x,
                    values_y,
                    card_w,
                    48,
                    color=self.LIVE_CARD,
                    border_color=(78, 94, 98),
                    alpha=0.9,
                    radius=10,
                )
                self._put_text(frame_bgr, label, x + 10, values_y + 18, 0.32, self.LIVE_MUTED)
                self._put_text(frame_bgr, f"{value:.1f}", x + 10, values_y + 40, 0.48, self.LIVE_TEXT, 2)
        else:
            self._put_text(
                frame_bgr,
                "No saved calibration yet. Defaults are used until calibration succeeds.",
                panel_x + 24,
                values_y + 28,
                0.4,
                self.LIVE_MUTED,
                max_width=panel_w - 48,
            )

        self._put_text(
            frame_bgr,
            "R reset/retry   |   Esc dashboard",
            panel_x + 24,
            panel_y + panel_h - 22,
            0.38,
            self.LIVE_MUTED,
            max_width=panel_w - 48,
        )

    def draw_settings(
        self,
        frame_bgr,
        settings,
        calibration_profile=None,
        camera_options=None,
    ) -> None:
        self._fill_background(frame_bgr)
        frame_h, frame_w = frame_bgr.shape[:2]
        margin = 34

        browser_hint = (
            "H show invalid tests"
            if getattr(settings, "hide_incomplete_sessions", False)
            else "H hide invalid tests"
        )
        self._draw_screen_header(
            frame_bgr,
            margin,
            "Settings",
            f"T toggle theme  |  K switch camera  |  {browser_hint}  |  R reset calibration  |  Esc dashboard",
        )

        panel_x = margin
        panel_y = 132
        panel_w = frame_w - (margin * 2)
        panel_h = min(420, frame_h - panel_y - margin)
        self._draw_panel(
            frame_bgr,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            color=self.PANEL,
            border_color=self.BORDER,
            alpha=0.96,
            radius=20,
        )

        self._put_text(
            frame_bgr,
            "Application Preferences",
            panel_x + 28,
            panel_y + 42,
            0.76,
            self.TEXT,
            2,
            max_width=panel_w - 56,
        )
        self._put_text(
            frame_bgr,
            "These settings are local to this device and do not change the squat-analysis model.",
            panel_x + 28,
            panel_y + 72,
            0.46,
            self.MUTED,
            max_width=panel_w - 56,
        )

        card_gap = 16
        card_y = panel_y + 112
        card_w = (panel_w - 56 - (card_gap * 3)) // 4
        theme_value = getattr(settings, "theme", "light").title()
        camera_index = getattr(settings, "camera_index", 0)
        camera_value = self._format_camera_display(
            camera_index,
            camera_options,
            include_index=True,
        )
        hides_invalid_tests = getattr(settings, "hide_incomplete_sessions", False)
        browser_value = (
            "Valid sessions only"
            if hides_invalid_tests
            else "Valid + invalid tests"
        )
        browser_helper = (
            "Press H to show invalid tests"
            if hides_invalid_tests
            else "Press H to hide invalid tests"
        )
        calibration_value = (
            "Calibrated"
            if calibration_profile
            else "Default thresholds"
        )
        cards = [
            ("Theme", theme_value, "Press T to switch light/dark", self.PRIMARY),
            ("Camera", camera_value, "Press K to cycle sources", self.INFO),
            ("Session Browser", browser_value, browser_helper, self.TEXT),
            (
                "Calibration",
                calibration_value,
                "Press R to reset calibration",
                self.WARNING if calibration_profile else self.MUTED,
            ),
        ]

        for index, (label, value, helper, value_color) in enumerate(cards):
            x = panel_x + 28 + ((card_w + card_gap) * index)
            self._draw_panel(
                frame_bgr,
                x,
                card_y,
                card_w,
                112,
                color=self.PANEL_ALT,
                border_color=self.BORDER,
                alpha=0.96,
                radius=16,
            )
            self._put_text(frame_bgr, label, x + 18, card_y + 28, 0.44, self.MUTED)
            self._put_text(
                frame_bgr,
                value,
                x + 18,
                card_y + 62,
                0.58,
                value_color,
                2 if index == 0 else 1,
                max_width=card_w - 36,
            )
            self._put_text(
                frame_bgr,
                helper,
                x + 18,
                card_y + 92,
                0.36,
                self.MUTED,
                max_width=card_w - 36,
            )

        camera_hint_y = card_y + 140
        self._put_text(
            frame_bgr,
            self._format_camera_options_line(camera_options),
            panel_x + 28,
            camera_hint_y,
            0.4,
            self.MUTED,
            max_width=panel_w - 56,
        )

        note_y = card_y + 174
        self._put_text(
            frame_bgr,
            "Safety note",
            panel_x + 28,
            note_y,
            0.58,
            self.TEXT,
            2,
            max_width=panel_w - 56,
        )
        self._put_text(
            frame_bgr,
            "Resetting calibration only removes user-specific thresholds. Session videos, summaries, and analytics are not deleted.",
            panel_x + 28,
            note_y + 30,
            0.44,
            self.MUTED,
            max_width=panel_w - 56,
        )

        self._put_text(
            frame_bgr,
            "Esc returns to dashboard.",
            panel_x + 28,
            panel_y + panel_h - 28,
            0.42,
            self.MUTED,
            max_width=panel_w - 56,
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

    def _draw_trends_panel(self, frame_bgr, x, y, width, height, snapshot) -> None:
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
            "Recent Trends",
            x + 24,
            y + 34,
            scale=0.66,
            color=self.TEXT,
            thickness=1,
            max_width=width - 48,
        )
        trend_sessions = list(getattr(snapshot, "trend_sessions", ()))
        if not trend_sessions:
            self._put_text(
                frame_bgr,
                "Last 15 meaningful sessions",
                x + 24,
                y + 60,
                scale=0.42,
                color=self.MUTED,
                max_width=width - 48,
            )
            self._put_text(
                frame_bgr,
                "No trend data available yet.",
                x + 24,
                y + 100,
                scale=0.52,
                color=self.MUTED,
                max_width=width - 48,
            )
            return

        visible_sessions = trend_sessions[:15]
        self._put_text(
            frame_bgr,
            f"Last 15 meaningful sessions - showing {len(visible_sessions)}",
            x + 24,
            y + 60,
            scale=0.46,
            color=self.MUTED,
            max_width=width - 48,
        )

        if len(visible_sessions) > 7:
            rows_per_col = 8
            row_h = 19
            row_gap = 1
            col_gap = 14
            col_w = (width - 48 - col_gap) // 2
            start_y = y + 80

            for index, item in enumerate(visible_sessions):
                col = index // rows_per_col
                row = index % rows_per_col
                row_x = x + 24 + (col * (col_w + col_gap))
                row_y = start_y + (row * (row_h + row_gap))
                row_color = self.PANEL_STRONG if index == 0 else self.PANEL_ALT
                self._draw_panel(
                    frame_bgr,
                    row_x,
                    row_y - 15,
                    col_w,
                    row_h,
                    color=row_color,
                    border_color=self.BORDER_ACTIVE if index == 0 else self.BORDER,
                    alpha=0.9,
                    radius=8,
                )
                stats = (
                    f"R{item.rep_count} "
                    f"B{self._format_compact_percentage(item.bad_rep_percentage)} "
                    f"K{self._format_compact_angle(item.avg_knee_angle)}"
                )
                self._put_text(
                    frame_bgr,
                    self._format_short_session_timestamp(item.folder_name),
                    row_x + 8,
                    row_y,
                    0.34,
                    self.TEXT if index == 0 else self.MUTED,
                    max_width=82,
                )
                self._put_text(
                    frame_bgr,
                    stats,
                    row_x + 98,
                    row_y,
                    0.34,
                    self.TEXT,
                    max_width=112,
                )
                self._put_text(
                    frame_bgr,
                    self._format_issue(item.most_common_issue),
                    row_x + 218,
                    row_y,
                    0.34,
                    self.WARNING if item.most_common_issue else self.PRIMARY,
                    max_width=col_w - 226,
                )
            return

        header_y = y + 78
        row_h = 18
        row_gap = 3
        session_x = x + 24
        reps_x = x + max(220, width - 420)
        bad_x = reps_x + 70
        knee_x = bad_x + 92
        issue_x = knee_x + 108

        self._put_text(frame_bgr, "Session", session_x, header_y, 0.36, self.MUTED)
        self._put_text(frame_bgr, "Reps", reps_x, header_y, 0.36, self.MUTED)
        self._put_text(frame_bgr, "Bad %", bad_x, header_y, 0.36, self.MUTED)
        self._put_text(frame_bgr, "Avg Knee", knee_x, header_y, 0.36, self.MUTED)
        self._put_text(frame_bgr, "Issue", issue_x, header_y, 0.36, self.MUTED)
        cv2.line(frame_bgr, (x + 22, y + 88), (x + width - 22, y + 88), self.BORDER, 1)

        row_y = y + 108
        for index, item in enumerate(visible_sessions):
            row_color = self.PANEL_STRONG if index == 0 else self.PANEL_ALT
            self._draw_panel(
                frame_bgr,
                x + 18,
                row_y - 15,
                width - 36,
                row_h,
                color=row_color,
                border_color=self.BORDER_ACTIVE if index == 0 else self.BORDER,
                alpha=0.9,
                radius=10,
            )
            self._put_text(
                frame_bgr,
                self._format_short_session_timestamp(item.folder_name),
                session_x,
                row_y,
                0.3,
                self.TEXT if index == 0 else self.MUTED,
                max_width=max(120, reps_x - session_x - 12),
            )
            self._put_text(frame_bgr, str(item.rep_count), reps_x, row_y, 0.3, self.TEXT)
            self._put_text(
                frame_bgr,
                self._format_percentage(item.bad_rep_percentage),
                bad_x,
                row_y,
                0.3,
                self.WARNING if (item.bad_rep_percentage or 0) > 0 else self.TEXT,
            )
            self._put_text(
                frame_bgr,
                self._format_angle(item.avg_knee_angle),
                knee_x,
                row_y,
                0.3,
                self.TEXT,
            )
            self._put_text(
                frame_bgr,
                self._format_issue(item.most_common_issue),
                issue_x,
                row_y,
                0.3,
                self.WARNING if item.most_common_issue else self.PRIMARY,
                max_width=x + width - issue_x - 24,
            )
            row_y += row_h + row_gap

        footer_y = y + height - 34
        self._put_text(
            frame_bgr,
            self._format_issue_totals_line(getattr(snapshot, "issue_totals", {})),
            x + 24,
            footer_y,
            0.34,
            self.MUTED,
            max_width=width - 48,
        )
        self._put_text(
            frame_bgr,
            self._format_fps_summary(snapshot),
            x + 24,
            footer_y + 18,
            0.34,
            self.MUTED,
            max_width=width - 48,
        )

    def _draw_progress_panel(self, frame_bgr, x, y, width, height, snapshot) -> None:
        compact = height < 160
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
            y + (30 if compact else 34),
            scale=0.54 if compact else 0.66,
            color=self.TEXT,
            thickness=1,
            max_width=width - 48,
        )
        self._put_text(
            frame_bgr,
            f"Previous: {self._format_session_timestamp(snapshot.previous_timestamp)}",
            x + 24,
            y + (52 if compact else 58),
            scale=0.42 if height < 160 else 0.5,
            color=self.MUTED,
            thickness=1,
            max_width=width - 48,
        )

        card_gap = 10
        card_w = (width - 48 - (card_gap * 2)) // 3
        card_y = y + 72 if compact else y + 92
        card_h = 36 if compact else 68
        self._draw_metric_tile(
            frame_bgr,
            x + 24,
            card_y,
            card_w,
            card_h,
            "Reps",
            self._format_change(snapshot.rep_count_change),
            self._change_color(snapshot.rep_count_change, positive_is_good=True),
            label_scale=0.34 if compact else 0.42,
            value_scale=0.36 if compact else 0.64,
        )
        self._draw_metric_tile(
            frame_bgr,
            x + 24 + card_w + card_gap,
            card_y,
            card_w,
            card_h,
            "Bad Rate",
            self._format_percentage_point_change(snapshot.bad_rep_percentage_change),
            self._change_color(
                snapshot.bad_rep_percentage_change, positive_is_good=False
            ),
            label_scale=0.34 if compact else 0.42,
            value_scale=0.31 if compact else 0.52,
        )
        self._draw_metric_tile(
            frame_bgr,
            x + 24 + ((card_w + card_gap) * 2),
            card_y,
            card_w,
            card_h,
            "Avg Knee",
            self._format_angle_change(snapshot.avg_knee_angle_change),
            self.TEXT,
            label_scale=0.34 if compact else 0.42,
            value_scale=0.31 if compact else 0.52,
        )

        if not compact:
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
            scale=0.56 if height < 160 else 0.66,
            color=self.TEXT,
            thickness=1,
            max_width=width - 48,
        )
        compact = height < 160
        if compact:
            rows = [
                ("Concern", snapshot.main_concern or "N/A", self.TEXT),
                ("Suggestion", snapshot.suggested_improvement or "N/A", self.MUTED),
                ("Focus", snapshot.focus_area or "N/A", self.PRIMARY),
            ]
            row_y = y + 58
            for label, value, color in rows:
                self._put_text(
                    frame_bgr,
                    f"{label}:",
                    x + 34,
                    row_y,
                    0.32,
                    self.MUTED,
                    max_width=92,
                )
                self._put_text(
                    frame_bgr,
                    value,
                    x + 116,
                    row_y,
                    0.32,
                    color,
                    max_width=width - 134,
                )
                row_y += 22
            return

        item_y = y + (48 if compact else 66)
        gap = 23 if compact else 42
        self._draw_report_item(
            frame_bgr,
            x + 34,
            item_y,
            width - 52,
            "Main concern",
            snapshot.main_concern or "N/A",
            self.TEXT,
            compact=compact,
        )
        self._draw_report_item(
            frame_bgr,
            x + 34,
            item_y + gap,
            width - 52,
            "Suggested improvement",
            snapshot.suggested_improvement or "N/A",
            self.MUTED,
            compact=compact,
        )
        self._draw_report_item(
            frame_bgr,
            x + 34,
            item_y + (gap * 2),
            width - 52,
            "Focus area",
            snapshot.focus_area or "N/A",
            self.PRIMARY,
            compact=compact,
        )

    def _draw_calibration_badge(
        self,
        frame_bgr,
        x: int,
        y: int,
        width: int,
        height: int,
        calibration_profile=None,
        *,
        compact: bool = False,
        live: bool = False,
    ) -> None:
        is_calibrated = calibration_profile is not None
        text = "Calibrated" if is_calibrated else "Default thresholds"

        if is_calibrated:
            if live or self.theme == "dark":
                fill = (43, 58, 24)
                border = (73, 110, 44)
                text_color = self.LIVE_BORDER if live else self.PRIMARY
            else:
                fill = self.PRIMARY_SOFT
                border = self.BORDER_ACTIVE
                text_color = self.PRIMARY
        else:
            fill = self.LIVE_CARD if live else self.PANEL_ALT
            border = self.BORDER if not live else (78, 94, 98)
            text_color = self.LIVE_MUTED if live else self.MUTED

        self._draw_panel(
            frame_bgr,
            x,
            y,
            width,
            height,
            color=fill,
            border_color=border,
            alpha=0.95 if not live else 0.88,
            radius=height // 2,
        )
        self._put_text_centered(
            frame_bgr,
            text,
            x,
            y,
            width,
            height,
            0.34 if compact else 0.38,
            text_color,
            1,
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
        calibration_profile=None,
    ) -> None:
        panel_x = 24
        panel_y = 24
        panel_w = 520
        panel_h = 210
        pad = 18

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
        self._draw_calibration_badge(
            frame_bgr,
            panel_x + panel_w - 166,
            panel_y + 16,
            150,
            24,
            calibration_profile,
            compact=True,
            live=True,
        )
        self._put_text(
            frame_bgr,
            state_text,
            panel_x + pad,
            panel_y + 66,
            scale=0.82,
            color=state_color,
            thickness=2,
            max_width=panel_w - (pad * 2),
        )

        chip_y = panel_y + 86
        chip_w = 142
        chip_gap = 12
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
                    panel_y + 184,
                    panel_w - (pad * 2),
                    feedback_message,
                    feedback_level,
                )
            return

        self._draw_compact_count(
            frame_bgr,
            panel_x + pad,
            panel_y + 126,
            118,
            "Reps",
            str(rep_counter.rep_count),
            self.LIVE_TEXT,
        )
        self._draw_compact_count(
            frame_bgr,
            panel_x + pad + 132,
            panel_y + 126,
            118,
            "Bad",
            str(rep_counter.bad_rep_count),
            self.ERROR if rep_counter.bad_rep_count else self.LIVE_TEXT,
        )

        if feedback_message:
            self._draw_live_focus_text(
                frame_bgr,
                panel_x + pad,
                panel_y + 190,
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
                panel_y + 190,
                scale=0.42,
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
            0.48,
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
        compact = height <= 64
        label_y = y + (16 if compact else 22)
        value_y = y + height - (7 if compact else 14)
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
        *,
        compact: bool = False,
    ) -> None:
        self._put_text(
            frame_bgr,
            label,
            x,
            y,
            0.34 if compact else 0.44,
            self.MUTED,
            max_width=width,
        )
        self._put_text(
            frame_bgr,
            value,
            x,
            y + (16 if compact else 24),
            scale=0.34 if compact else 0.54,
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
        scale = 1.08
        thickness = 2
        _, frame_w = frame_bgr.shape[:2]
        max_panel_w = min(680, max(360, frame_w - 560))
        pad_x = 24
        pad_y = 18
        text_max_w = max_panel_w - (pad_x * 2)
        lines = self._wrap_text(message, text_max_w, scale, thickness, max_lines=3)
        text_w = max(self._text_width(line, scale, thickness) for line in lines)
        text_h = self._text_height("Ag", scale, thickness)
        line_gap = 8
        panel_w = max(360, min(max_panel_w, text_w + (pad_x * 2)))
        panel_h = (text_h * len(lines)) + (line_gap * (len(lines) - 1)) + (pad_y * 2)
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
            alpha=0.92,
            radius=18,
        )
        text_y = panel_y + pad_y + text_h
        for line in lines:
            self._put_text(
                frame_bgr,
                line,
                panel_x + pad_x,
                text_y,
                scale=scale,
                color=color,
                thickness=thickness,
                max_width=None,
            )
            text_y += text_h + line_gap

    def _draw_pill(
        self,
        frame_bgr,
        x: int,
        y: int,
        text: str,
        text_color: tuple[int, int, int],
        fill_color: tuple[int, int, int],
    ) -> None:
        scale = 0.44
        text_w = self._text_width(text, scale, 1)
        width = text_w + 28
        height = 32
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
        self._put_text_centered(
            frame_bgr, text, x, y, width, height, scale, text_color
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
        self._put_text(frame_bgr, label.upper(), x + 18, y + 28, 0.34, self.MUTED)
        self._put_text(
            frame_bgr, value, x + 18, y + 58, 0.43, self.TEXT, max_width=width - 36
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
        key_box_w = 58 if key != "Esc" else 76
        key_box_h = 48
        key_box_x = x + 18
        key_box_y = y + ((height - key_box_h) // 2)
        self._draw_panel(
            frame_bgr,
            key_box_x,
            key_box_y,
            key_box_w,
            key_box_h,
            color=self.SELECTED,
            border_color=self.BORDER_ACTIVE,
            alpha=0.95,
            radius=12,
        )
        self._put_text_centered(
            frame_bgr,
            key,
            key_box_x,
            key_box_y,
            key_box_w,
            key_box_h,
            0.5,
            self.PRIMARY,
            2,
        )
        text_x = key_box_x + key_box_w + 24
        title_y = y + 34
        subtitle_y = y + 61
        self._put_text(
            frame_bgr,
            title,
            text_x,
            title_y,
            0.62,
            self.TEXT,
            2,
            max_width=width - (text_x - x) - 24,
        )
        self._put_text(
            frame_bgr,
            subtitle,
            text_x,
            subtitle_y,
            0.43,
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

        if self.theme == "dark":
            texture_color = (55, 47, 39)
            texture_alpha = 0.18
            header_color = (31, 27, 23)
            header_border = (67, 57, 48)
            glow_primary = (74, 92, 36)
            glow_secondary = (50, 43, 37)
            glow_alpha = 0.26
            footer_color = (68, 78, 32)
        else:
            texture_color = (231, 239, 234)
            texture_alpha = 0.14
            header_color = (248, 252, 249)
            header_border = (199, 215, 203)
            glow_primary = (224, 243, 230)
            glow_secondary = (238, 245, 241)
            glow_alpha = 0.24
            footer_color = (206, 226, 213)

        texture = frame_bgr.copy()
        for x in range(-frame_h, frame_w, 92):
            cv2.line(texture, (x, frame_h), (x + frame_h, 0), texture_color, 1)
        cv2.addWeighted(texture, texture_alpha, frame_bgr, 1 - texture_alpha, 0, frame_bgr)

        cv2.rectangle(frame_bgr, (0, 0), (frame_w, 104), header_color, -1)
        cv2.line(frame_bgr, (0, 104), (frame_w, 104), header_border, 1)
        cv2.line(frame_bgr, (0, 105), (frame_w, 105), self.PRIMARY, 2)

        glow = frame_bgr.copy()
        cv2.circle(glow, (frame_w - 120, 78), 210, glow_primary, -1)
        cv2.circle(glow, (92, frame_h - 76), 180, glow_secondary, -1)
        cv2.addWeighted(glow, glow_alpha, frame_bgr, 1 - glow_alpha, 0, frame_bgr)
        cv2.rectangle(frame_bgr, (0, frame_h - 6), (frame_w, frame_h), footer_color, -1)

    def _draw_panel(
        self,
        frame_bgr,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple[int, int, int] | None = None,
        border_color: tuple[int, int, int] | None = None,
        alpha: float = 0.88,
        radius: int = 14,
    ) -> None:
        color = self.PANEL if color is None else color
        border_color = self.BORDER if border_color is None else border_color
        is_live_panel = color in (self.LIVE_PANEL, self.LIVE_CARD)
        if self.theme == "light" and not is_live_panel and width >= 180 and height >= 54:
            shadow = frame_bgr.copy()
            self._draw_rounded_rect(
                shadow,
                x + 4,
                y + 6,
                width,
                height,
                radius,
                (178, 199, 185),
                -1,
            )
            cv2.addWeighted(shadow, 0.10, frame_bgr, 0.90, 0, frame_bgr)

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

    def _wrap_text(
        self,
        text: str,
        max_width: int,
        scale: float,
        thickness: int,
        *,
        max_lines: int = 3,
    ) -> list[str]:
        if max_width <= 0:
            return ["..."]

        words = text.split()
        if not words:
            return [""]

        lines: list[str] = []
        current = ""
        index = 0
        while index < len(words):
            word = words[index]
            candidate = word if not current else f"{current} {word}"
            if self._text_width(candidate, scale, thickness) <= max_width:
                current = candidate
                index += 1
                continue

            if current:
                lines.append(current)
                current = ""
                if len(lines) >= max_lines:
                    return lines[:max_lines]
                continue

            lines.append(self._fit_text(word, max_width, scale, thickness))
            index += 1
            if len(lines) >= max_lines:
                return lines[:max_lines]

        if current:
            lines.append(current)

        if len(lines) <= max_lines:
            return lines

        visible = lines[: max_lines - 1]
        remaining = " ".join(lines[max_lines - 1 :])
        visible.append(self._fit_text(remaining, max_width, scale, thickness))
        return visible

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
        return max(10, int(round(scale * 36)))

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
    def _format_compact_percentage(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.0f}%"

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
    def _format_compact_angle(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.0f}"

    @staticmethod
    def _format_fps(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.1f}"

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

    def _format_issue_totals_line(self, issue_totals: dict[str, int]) -> str:
        if not issue_totals:
            return "Issue totals: none recorded"

        parts = []
        for issue, count in list(issue_totals.items())[:3]:
            parts.append(f"{self._format_issue(issue)} {count}")
        return "Issue totals: " + " | ".join(parts)

    def _format_fps_summary(self, snapshot) -> str:
        latest = self._format_fps(getattr(snapshot, "latest_avg_fps", None))
        overall = self._format_fps(getattr(snapshot, "avg_fps_overall", None))
        return f"FPS: latest {latest} | overall average {overall}"

    @staticmethod
    def _camera_fallback_label(index: int) -> str:
        labels = {
            0: "Default / built-in",
            1: "External USB",
            2: "Phone / virtual",
        }
        return labels.get(index, f"Camera {index}")

    def _format_camera_display(
        self,
        camera_index: int,
        camera_options=None,
        *,
        include_index: bool = False,
    ) -> str:
        label = self._camera_fallback_label(camera_index)
        if camera_options:
            for option in camera_options:
                if int(option.get("index", -1)) == camera_index:
                    label = str(option.get("label") or label)
                    break
        return f"{camera_index} - {label}" if include_index else label

    def _format_camera_options_line(self, camera_options=None) -> str:
        if not camera_options:
            return "Camera labels: 0 Default / built-in | 1 External USB | 2 Phone / virtual"

        parts = []
        for option in camera_options:
            index = int(option.get("index", 0))
            label = str(option.get("label") or self._camera_fallback_label(index))
            parts.append(f"{index} {label}")
        return "Camera sources: " + "  |  ".join(parts)

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
        prefix = ""
        if value.startswith("video_"):
            prefix = "Video "
            value = value[len("video_") :]
        if len(value) == 15 and "_" in value:
            date_part, time_part = value.split("_", maxsplit=1)
            if len(date_part) == 8 and len(time_part) == 6:
                return (
                    f"{prefix}{date_part[0:4]}-{date_part[4:6]}-{date_part[6:8]} "
                    f"{time_part[0:2]}:{time_part[2:4]}:{time_part[4:6]}"
                )
        return f"{prefix}{value}"

    @staticmethod
    def _format_short_session_timestamp(value: str | None) -> str:
        if not value:
            return "N/A"
        if value.startswith("video_"):
            value = value[len("video_") :]
        if len(value) == 15 and "_" in value:
            date_part, time_part = value.split("_", maxsplit=1)
            if len(date_part) == 8 and len(time_part) == 6:
                return (
                    f"{date_part[4:6]}-{date_part[6:8]} "
                    f"{time_part[0:2]}:{time_part[2:4]}"
                )
        return value
