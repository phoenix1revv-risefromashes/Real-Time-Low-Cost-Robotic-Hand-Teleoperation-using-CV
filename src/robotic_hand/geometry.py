"""Pure vision geometry; no camera, GPIO, or serial side effects."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import NamedTuple

from robotic_hand.config import FINGERS, FingerConfig


class Point(NamedTuple):
    x: float
    y: float


# MediaPipe hand indices: 0 wrist, 4 thumb tip, 8/12/16/20 fingertip, 17 pinky MCP.
TIP_TO_REFERENCE = {"thumb": (4, 17), "index": (8, 0), "middle": (12, 0),
                    "ring": (16, 0), "pinky": (20, 0)}
PALM_WIDTH_POINTS = (5, 17)  # index MCP to pinky MCP


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def normalized_finger_metrics(landmarks: Sequence[Point]) -> dict[str, float]:
    """Distance ratios largely invariant to apparent hand size.

    These are geometric heuristics, *not* estimates of actual joint angles.
    """
    if len(landmarks) != 21:
        raise ValueError("Expected exactly 21 landmarks")
    if not all(math.isfinite(v) and 0 <= v <= 1 for point in landmarks for v in point):
        raise ValueError("All landmarks must be finite and in the normalized image bounds")
    width = _distance(landmarks[5], landmarks[17])
    if width < 0.025:
        raise ValueError("Palm scale too small; hand may be out of view or occluded")
    return {
        name: _distance(landmarks[tip], landmarks[reference]) / width
        for name, (tip, reference) in TIP_TO_REFERENCE.items()
    }


def metric_to_servo_angle(metric: float, calibration: FingerConfig) -> float:
    """Linear calibrated ratio->servo mapping, with endpoint clamping.

    Reversing servo_closed_deg/servo_open_deg reverses motor direction.
    """
    if not math.isfinite(metric):
        raise ValueError("Invalid finger metric")
    t = (metric - calibration.metric_closed) / (
        calibration.metric_open - calibration.metric_closed
    )
    t = min(1.0, max(0.0, t))
    return calibration.servo_closed_deg + t * (
        calibration.servo_open_deg - calibration.servo_closed_deg
    )


def angles_from_landmarks(
    landmarks: Sequence[Point], calibration: dict[str, FingerConfig]
) -> dict[str, float]:
    metrics = normalized_finger_metrics(landmarks)
    return {name: metric_to_servo_angle(metrics[name], calibration[name]) for name in FINGERS}
