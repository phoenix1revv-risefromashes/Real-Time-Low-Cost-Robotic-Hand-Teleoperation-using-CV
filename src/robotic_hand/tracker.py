"""MediaPipe Tasks adapter; imported lazily so core and tests are dependency-light."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from robotic_hand.geometry import Point


class HandTracker:
    def __init__(self, model_path: str | Path) -> None:
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError("Install vision extras: pip install -e '.[vision]'") from exc
        if not Path(model_path).is_file():
            raise FileNotFoundError(f"Hand Landmarker task model missing: {model_path}")
        self._mp: Any = mp
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self._tracker: Any = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self._last_ms = -1

    def detect(self, bgr_frame: Any, timestamp_ms: int) -> list[Point] | None:
        import cv2

        # The tracker expects strictly increasing timestamps; avoid duplicates.
        timestamp_ms = max(timestamp_ms, self._last_ms + 1)
        self._last_ms = timestamp_ms
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._tracker.detect_for_video(mp_image, timestamp_ms)
        if not result.hand_landmarks:
            return None
        return [Point(float(point.x), float(point.y)) for point in result.hand_landmarks[0]]

    def close(self) -> None:
        self._tracker.close()
