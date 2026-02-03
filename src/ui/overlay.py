"""Overlay rendering for pose landmarks and squat state (Tasks API result)."""

from __future__ import annotations

import cv2


class OverlayRenderer:
    def draw(self, frame_bgr, results, squat_state, rep_counter=None) -> None:
        # results.pose_landmarks is a list (per detected pose), each is list of landmarks
        if results and getattr(results, "pose_landmarks", None):
            if len(results.pose_landmarks) > 0:
                landmarks = results.pose_landmarks[0]
                h, w = frame_bgr.shape[:2]

                # Draw keypoints as circles
                for lm in landmarks:
                    x = int(lm.x * w)
                    y = int(lm.y * h)
                    cv2.circle(frame_bgr, (x, y), 3, (0, 255, 0), -1)

                # Optional simple stick connections can be added later.
                # For MVP, keypoints are enough to confirm tracking works.

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
