"""Overlay rendering for workout, dashboard, and browser screens."""

from __future__ import annotations

import cv2


class OverlayRenderer:
    """Draw consistent OpenCV UI overlays without changing app behavior."""

    FONT = cv2.FONT_HERSHEY_DUPLEX

    BG = (15, 15, 15)
    BG_SOFT = (22, 22, 22)
    PANEL = (28, 28, 28)
    PANEL_ALT = (36, 36, 36)
    BORDER = (62, 62, 62)
    BORDER_ACTIVE = (86, 170, 110)

    PRIMARY = (92, 220, 132)
    WARNING = (0, 165, 255)
    ERROR = (68, 86, 235)
    TEXT = (232, 232, 232)
    MUTED = (166, 166, 166)
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
        self._draw_session_panel(frame_bgr, squat_state, rep_counter)

        if feedback_message:
            self._draw_feedback(frame_bgr, feedback_message, feedback_level)

    def draw_dashboard(self, frame_bgr) -> None:
        self._fill_background(frame_bgr)
        frame_h, frame_w = frame_bgr.shape[:2]
        panel_w = min(780, frame_w - 140)
        panel_h = 450
        panel_x = (frame_w - panel_w) // 2
        panel_y = max(70, (frame_h - panel_h) // 2)

        self._draw_panel(
            frame_bgr,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            border_color=self.BORDER_ACTIVE,
            alpha=0.94,
        )
        self._put_text(
            frame_bgr,
            "GymGuardian",
            panel_x + 46,
            panel_y + 82,
            scale=1.55,
            color=self.PRIMARY,
            thickness=2,
            max_width=panel_w - 92,
        )
        self._put_text(
            frame_bgr,
            "Real-time posture correction for home workouts",
            panel_x + 50,
            panel_y + 126,
            scale=0.66,
            color=self.MUTED,
            thickness=1,
            max_width=panel_w - 100,
        )

        options = [
            ("S", "Start squat session"),
            ("B", "Browse saved sessions"),
            ("A", "Open analytics dashboard"),
            ("Esc", "Quit application"),
        ]
        row_y = panel_y + 190
        for key, label in options:
            self._draw_menu_row(
                frame_bgr,
                panel_x + 48,
                row_y,
                panel_w - 96,
                key,
                label,
            )
            row_y += 64

        self._put_text(
            frame_bgr,
            "Press the highlighted key to continue. Use Esc to close or go back from menus.",
            panel_x + 50,
            panel_y + panel_h - 30,
            scale=0.48,
            color=self.MUTED,
            thickness=1,
            max_width=panel_w - 100,
        )

    def draw_browser(self, frame_bgr, sessions, selected_index: int) -> None:
        self._fill_background(frame_bgr)
        frame_h, frame_w = frame_bgr.shape[:2]

        margin = 36
        self._put_text(
            frame_bgr,
            "Session Browser",
            margin,
            58,
            scale=1.18,
            color=self.PRIMARY,
            thickness=2,
        )
        self._put_text(
            frame_bgr,
            "Up/Down: select    P: play video    O: open folder    Esc: dashboard",
            margin + 2,
            96,
            scale=0.58,
            color=self.MUTED,
            thickness=1,
            max_width=frame_w - (margin * 2),
        )

        list_x = margin
        list_y = 132
        list_w = frame_w - (margin * 2)
        list_h = frame_h - list_y - margin
        reps_x = list_x + list_w - 230
        bad_x = list_x + list_w - 125
        timestamp_w = max(240, reps_x - list_x - 48)

        self._draw_panel(
            frame_bgr,
            list_x,
            list_y,
            list_w,
            list_h,
            border_color=self.BORDER,
            alpha=0.9,
        )

        if not sessions:
            self._put_text(
                frame_bgr,
                "No saved sessions found in /sessions",
                list_x + 28,
                list_y + 74,
                scale=0.72,
                color=self.MUTED,
                thickness=1,
                max_width=list_w - 56,
            )
            return

        header_y = list_y + 42
        self._put_text(
            frame_bgr,
            "Timestamp",
            list_x + 28,
            header_y,
            scale=0.56,
            color=self.MUTED,
            thickness=1,
        )
        self._put_text(
            frame_bgr,
            "Reps",
            reps_x,
            header_y,
            scale=0.56,
            color=self.MUTED,
            thickness=1,
        )
        self._put_text(
            frame_bgr,
            "Bad",
            bad_x,
            header_y,
            scale=0.56,
            color=self.MUTED,
            thickness=1,
        )
        cv2.line(
            frame_bgr,
            (list_x + 22, list_y + 58),
            (list_x + list_w - 22, list_y + 58),
            self.BORDER,
            1,
        )

        max_rows = max(1, (list_h - 84) // 46)
        start = min(
            max(0, selected_index - max_rows // 2),
            max(0, len(sessions) - max_rows),
        )
        end = min(len(sessions), start + max_rows)
        row_y = list_y + 94
        row_h = 42

        for idx in range(start, end):
            item = sessions[idx]
            selected = idx == selected_index
            reps = "?" if item.rep_count is None else str(item.rep_count)
            bad = "?" if item.bad_rep_count is None else str(item.bad_rep_count)

            if selected:
                self._draw_panel(
                    frame_bgr,
                    list_x + 16,
                    row_y - 29,
                    list_w - 32,
                    row_h,
                    color=self.PANEL_ALT,
                    border_color=self.BORDER_ACTIVE,
                    alpha=0.96,
                )

            color = self.TEXT if selected else (205, 205, 205)
            marker = ">" if selected else " "
            self._put_text(
                frame_bgr,
                f"{marker} {item.folder_name}",
                list_x + 30,
                row_y,
                scale=0.66,
                color=color,
                thickness=1,
                max_width=timestamp_w,
            )
            self._put_text(
                frame_bgr,
                reps,
                reps_x,
                row_y,
                scale=0.66,
                color=color,
                thickness=1,
                max_width=64,
            )
            self._put_text(
                frame_bgr,
                bad,
                bad_x,
                row_y,
                scale=0.66,
                color=self.ERROR if bad not in ("0", "?") else color,
                thickness=1,
                max_width=64,
            )
            row_y += 46

    def draw_analytics(self, frame_bgr, snapshot) -> None:
        self._fill_background(frame_bgr)
        frame_h, frame_w = frame_bgr.shape[:2]
        margin = 36
        compact_layout = frame_h < 900

        self._put_text(
            frame_bgr,
            "Analytics Dashboard",
            margin,
            58,
            scale=1.18,
            color=self.PRIMARY,
            thickness=2,
        )
        self._put_text(
            frame_bgr,
            "R: refresh    Esc: dashboard",
            margin + 2,
            96,
            scale=0.58,
            color=self.MUTED,
            thickness=1,
            max_width=frame_w - (margin * 2),
        )

        summary_x = margin
        summary_y = 132
        summary_w = frame_w - (margin * 2)
        progress_gap = 20
        min_progress_h = 194 if compact_layout else 220
        desired_summary_h = 338 if compact_layout else 392
        available_h = frame_h - summary_y - margin
        summary_h = min(desired_summary_h, available_h - progress_gap - min_progress_h)
        summary_h = max(258 if compact_layout else 320, summary_h)
        self._draw_panel(
            frame_bgr,
            summary_x,
            summary_y,
            summary_w,
            summary_h,
            border_color=self.BORDER,
            alpha=0.9,
        )

        self._put_text(
            frame_bgr,
            "Latest Meaningful Session",
            summary_x + 28,
            summary_y + 42,
            scale=0.72,
            color=self.TEXT,
            thickness=1,
        )

        has_meaningful_data = snapshot.meaningful_session_count > 0
        if not has_meaningful_data:
            self._put_text(
                frame_bgr,
                "No meaningful session data available.",
                summary_x + 28,
                summary_y + 90,
                scale=0.72,
                color=self.TEXT,
                thickness=1,
                max_width=summary_w - 56,
            )
            self._put_text(
                frame_bgr,
                (
                    "Saved session folders exist, but none contain completed workout data yet."
                    if snapshot.total_sessions > 0
                    else "Complete and save a workout session to populate analytics."
                ),
                summary_x + 28,
                summary_y + 118,
                scale=0.54,
                color=self.MUTED,
                thickness=1,
                max_width=summary_w - 56,
            )
        else:
            timestamp_text = self._format_session_timestamp(snapshot.latest_timestamp)
            self._put_text(
                frame_bgr,
                f"Latest session: {timestamp_text}",
                summary_x + 28,
                summary_y + 84,
                scale=0.62,
                color=self.MUTED,
                thickness=1,
                max_width=summary_w - 56,
            )

        summary_cards_y = summary_y + (
            148 if not has_meaningful_data and compact_layout else
            160 if not has_meaningful_data else
            116 if compact_layout else
            122
        )
        cards_x = summary_x + 24
        cards_gap = 16
        cards_w = summary_w - 48
        card_w = (cards_w - (cards_gap * 2)) // 3
        card_h = 60 if not has_meaningful_data else 72 if compact_layout else 84
        row_gap = 10 if compact_layout else 12
        issue_h = 44 if compact_layout else 52

        self._draw_metric_tile(
            frame_bgr,
            cards_x,
            summary_cards_y,
            card_w,
            card_h,
            "Total Sessions",
            str(snapshot.total_sessions),
            self.PRIMARY,
        )
        self._put_text(
            frame_bgr,
            f"Meaningful sessions: {snapshot.meaningful_session_count}",
            summary_x + 28,
            summary_y + (136 if not has_meaningful_data else 104 if compact_layout else 110),
            scale=0.58,
            color=self.MUTED,
            thickness=1,
            max_width=summary_w - 56,
        )

        self._draw_metric_tile(
            frame_bgr,
            cards_x + card_w + cards_gap,
            summary_cards_y,
            card_w,
            card_h,
            "Latest Reps",
            self._format_metric_value(snapshot.latest_rep_count),
            self.TEXT,
        )
        self._draw_metric_tile(
            frame_bgr,
            cards_x + ((card_w + cards_gap) * 2),
            summary_cards_y,
            card_w,
            card_h,
            "Latest Bad Reps",
            self._format_metric_value(snapshot.latest_bad_rep_count),
            self.ERROR if (snapshot.latest_bad_rep_count or 0) > 0 else self.TEXT,
        )

        second_row_y = summary_cards_y + card_h + row_gap
        self._draw_metric_tile(
            frame_bgr,
            cards_x,
            second_row_y,
            card_w,
            card_h,
            "Bad Rep Rate",
            self._format_percentage(snapshot.latest_bad_rep_percentage),
            self.WARNING if (snapshot.latest_bad_rep_percentage or 0.0) > 0 else self.TEXT,
        )
        self._draw_metric_tile(
            frame_bgr,
            cards_x + card_w + cards_gap,
            second_row_y,
            card_w,
            card_h,
            "Avg Knee Angle",
            self._format_angle(snapshot.latest_avg_knee_angle),
            self.TEXT,
        )
        self._draw_metric_tile(
            frame_bgr,
            cards_x + ((card_w + cards_gap) * 2),
            second_row_y,
            card_w,
            card_h,
            "Min Knee Angle",
            self._format_angle(snapshot.latest_min_knee_angle),
            self.TEXT,
        )

        issue_text = self._format_issue(snapshot.latest_most_common_issue)
        issue_y = second_row_y + card_h + row_gap
        self._draw_metric_tile(
            frame_bgr,
            cards_x,
            issue_y,
            cards_w,
            issue_h,
            "Most Common Issue",
            issue_text,
            self.TEXT,
            label_scale=0.46,
            value_scale=0.54 if compact_layout else 0.6,
        )

        progress_x = margin
        progress_y = summary_y + summary_h + progress_gap
        progress_w = frame_w - (margin * 2)
        progress_h = frame_h - progress_y - margin
        self._draw_panel(
            frame_bgr,
            progress_x,
            progress_y,
            progress_w,
            progress_h,
            border_color=self.BORDER,
            alpha=0.9,
        )
        self._put_text(
            frame_bgr,
            "Progress vs Previous Meaningful Session",
            progress_x + 28,
            progress_y + (38 if compact_layout else 42),
            scale=0.72,
            color=self.TEXT,
            thickness=1,
        )

        previous_timestamp_text = self._format_session_timestamp(snapshot.previous_timestamp)
        self._put_text(
            frame_bgr,
            f"Previous meaningful session: {previous_timestamp_text}",
            progress_x + 28,
            progress_y + (68 if compact_layout else 74),
            scale=0.58,
            color=self.MUTED,
            thickness=1,
            max_width=progress_w - 56,
        )

        previous_text = self._format_metric_value(snapshot.previous_rep_count)
        self._put_text(
            frame_bgr,
            f"Previous rep count: {previous_text}",
            progress_x + 28,
            progress_y + (92 if compact_layout else 100),
            scale=0.6,
            color=self.MUTED,
            thickness=1,
            max_width=progress_w - 56,
        )

        delta_cards_y = progress_y + (110 if compact_layout else 124)
        delta_card_w = (progress_w - 72) // 2
        delta_card_h = 60 if compact_layout else 72

        rep_delta_text = self._format_change(snapshot.rep_count_change)
        rep_delta_color = self._change_color(snapshot.rep_count_change, positive_is_good=True)
        self._draw_metric_tile(
            frame_bgr,
            progress_x + 24,
            delta_cards_y,
            delta_card_w,
            delta_card_h,
            "Rep Count Change",
            rep_delta_text,
            rep_delta_color,
        )

        bad_delta_text = self._format_change(snapshot.bad_rep_count_change)
        bad_delta_color = self._change_color(
            snapshot.bad_rep_count_change,
            positive_is_good=False,
        )
        self._draw_metric_tile(
            frame_bgr,
            progress_x + 40 + delta_card_w,
            delta_cards_y,
            delta_card_w,
            delta_card_h,
            "Bad Rep Change",
            bad_delta_text,
            bad_delta_color,
        )

    def draw_debug(self, frame_bgr, debug_info: dict) -> None:
        lines = [
            "Debug (D to toggle)",
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
        panel_y = 194
        line_height = 26
        panel_w = 460
        panel_h = 24 + line_height * len(lines)
        self._draw_panel(
            frame_bgr,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            border_color=self.WARNING,
            alpha=0.86,
        )

        y = panel_y + 28
        for line in lines:
            self._put_text(
                frame_bgr,
                line,
                panel_x + 14,
                y,
                scale=0.54,
                color=self.TEXT,
                thickness=1,
                max_width=panel_w - 28,
            )
            y += line_height

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

    def _draw_session_panel(self, frame_bgr, squat_state, rep_counter=None) -> None:
        panel_x = 20
        panel_y = 20
        panel_w = 470
        panel_h = 184
        pad = 18

        self._draw_panel(
            frame_bgr,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            border_color=self.BORDER,
            alpha=0.84,
        )

        state_text = squat_state.label.replace("_", " ").title()
        self._put_text(
            frame_bgr,
            f"State: {state_text}",
            panel_x + pad,
            panel_y + 38,
            scale=0.78,
            color=self.PRIMARY,
            thickness=1,
            max_width=panel_w - (pad * 2),
        )

        if squat_state.knee_angle is None:
            knee_text = "Knee angle: n/a"
        else:
            knee_text = f"Knee angle: {squat_state.knee_angle:.1f}"
        self._put_text(
            frame_bgr,
            knee_text,
            panel_x + pad,
            panel_y + 72,
            scale=0.64,
            color=self.TEXT,
            thickness=1,
            max_width=panel_w - (pad * 2),
        )

        if rep_counter is None:
            return

        reps_y = panel_y + 112
        self._put_text(
            frame_bgr,
            f"Reps: {rep_counter.rep_count}",
            panel_x + pad,
            reps_y,
            scale=0.7,
            color=self.TEXT,
            thickness=1,
            max_width=120,
        )
        self._put_text(
            frame_bgr,
            f"Bad: {rep_counter.bad_rep_count}",
            panel_x + 150,
            reps_y,
            scale=0.7,
            color=self.ERROR if rep_counter.bad_rep_count else self.TEXT,
            thickness=1,
            max_width=110,
        )

        last_text = self._format_result(rep_counter.last_rep_result)
        self._put_text(
            frame_bgr,
            f"Last: {last_text}",
            panel_x + pad,
            panel_y + 144,
            scale=0.56,
            color=self.MUTED,
            thickness=1,
            max_width=panel_w - (pad * 2),
        )
        self._put_text(
            frame_bgr,
            "Esc: end session    D: debug overlay",
            panel_x + pad,
            panel_y + 170,
            scale=0.48,
            color=self.MUTED,
            thickness=1,
            max_width=panel_w - (pad * 2),
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
        label_scale: float = 0.5,
        value_scale: float | None = None,
    ) -> None:
        compact_tile = height < 72
        label_y = y + (24 if compact_tile else 28)
        value_y = y + height - (14 if compact_tile else 18)
        if value_scale is None:
            value_scale = 0.72 if compact_tile else 0.88

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
            x + 16,
            label_y,
            scale=label_scale,
            color=self.MUTED,
            thickness=1,
            max_width=width - 32,
        )
        self._put_text(
            frame_bgr,
            value,
            x + 16,
            value_y,
            scale=value_scale,
            color=value_color,
            thickness=1,
            max_width=width - 32,
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
        scale = 0.86
        thickness = 1
        _, frame_w = frame_bgr.shape[:2]
        max_panel_w = min(430, frame_w - 540)
        display_text = self._fit_text(message, max_panel_w - 36, scale, thickness)
        text_size, _ = cv2.getTextSize(display_text, self.FONT, scale, thickness)
        text_w, text_h = text_size
        pad_x = 18
        pad_y = 14
        panel_w = max(240, text_w + (pad_x * 2))
        panel_h = text_h + (pad_y * 2)
        panel_x = frame_w - panel_w - 24
        panel_y = 24

        self._draw_panel(
            frame_bgr,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            border_color=color,
            alpha=0.88,
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

    def _draw_menu_row(
        self, frame_bgr, x: int, y: int, width: int, key: str, label: str
    ) -> None:
        row_h = 48
        key_scale = 0.62
        key_thickness = 1
        key_width = self._text_width(key, key_scale, key_thickness)
        key_box_w = max(36, key_width + 20)
        key_box_x = x + 18

        self._draw_panel(
            frame_bgr,
            x,
            y - 32,
            width,
            row_h,
            color=self.PANEL_ALT,
            border_color=self.BORDER,
            alpha=0.94,
        )
        cv2.rectangle(
            frame_bgr,
            (key_box_x, y - 24),
            (key_box_x + key_box_w, y + 10),
            self.BG_SOFT,
            -1,
        )
        cv2.rectangle(
            frame_bgr,
            (key_box_x, y - 24),
            (key_box_x + key_box_w, y + 10),
            self.PRIMARY,
            1,
        )
        self._put_text(
            frame_bgr,
            key,
            key_box_x + ((key_box_w - key_width) // 2),
            y,
            scale=key_scale,
            color=self.PRIMARY,
            thickness=key_thickness,
            max_width=key_box_w - 12,
        )
        self._put_text(
            frame_bgr,
            label,
            key_box_x + key_box_w + 22,
            y,
            scale=0.68,
            color=self.TEXT,
            thickness=1,
            max_width=width - key_box_w - 58,
        )

    def _fill_background(self, frame_bgr) -> None:
        frame_bgr[:] = self.BG
        frame_h, frame_w = frame_bgr.shape[:2]
        cv2.rectangle(frame_bgr, (0, 0), (frame_w, 112), self.BG_SOFT, -1)
        cv2.line(frame_bgr, (0, 112), (frame_w, 112), self.BORDER, 1)
        cv2.circle(frame_bgr, (frame_w - 100, 80), 150, (20, 32, 24), -1)
        cv2.circle(frame_bgr, (70, frame_h - 70), 130, (24, 24, 24), -1)

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
    ) -> None:
        overlay = frame_bgr.copy()
        cv2.rectangle(overlay, (x, y), (x + width, y + height), color, -1)
        cv2.addWeighted(overlay, alpha, frame_bgr, 1 - alpha, 0, frame_bgr)
        cv2.rectangle(frame_bgr, (x, y), (x + width, y + height), border_color, 1)

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

        cv2.putText(
            frame_bgr,
            display_text,
            (x + 1, y + 1),
            self.FONT,
            scale,
            self.SHADOW,
            thickness + 1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame_bgr,
            display_text,
            (x, y),
            self.FONT,
            scale,
            color,
            thickness,
            cv2.LINE_AA,
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
        text_size, _ = cv2.getTextSize(text, self.FONT, scale, thickness)
        return text_size[0]

    @staticmethod
    def _format_result(value: str) -> str:
        if not value or value == "none":
            return "none"
        return value

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
    def _format_angle(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.1f} deg"

    @staticmethod
    def _format_issue(value: str | None) -> str:
        if not value:
            return "none"
        return value.replace("_", " ")

    def _change_color(
        self, value: int | None, *, positive_is_good: bool
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
