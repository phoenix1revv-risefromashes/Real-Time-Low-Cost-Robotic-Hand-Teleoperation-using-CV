import math

import pytest

from robotic_hand.geometry import (
    Point,
    metric_to_servo_angle,
    normalized_finger_metrics,
)


def test_metrics_are_scale_invariant():
    points = [Point(0.5, 0.5) for _ in range(21)]
    points[5], points[17] = Point(0.35, 0.5), Point(0.65, 0.5)
    points[8] = Point(0.5, 0.1)
    original = normalized_finger_metrics(points)
    scaled = [Point((p.x - 0.5) * 0.5 + 0.5, (p.y - 0.5) * 0.5 + 0.5) for p in points]
    other = normalized_finger_metrics(scaled)
    assert original["index"] == pytest.approx(other["index"])


def test_rejects_bad_landmarks():
    with pytest.raises(ValueError):
        normalized_finger_metrics([Point(0, 0)])
    with pytest.raises(ValueError):
        normalized_finger_metrics([Point(0.5, 0.5)] * 21)
    points = [Point(0.5, 0.5)] * 21
    points[0] = Point(math.nan, 0.5)
    with pytest.raises(ValueError):
        normalized_finger_metrics(points)


def test_mapping_clamps_and_reverse(cfg):
    f = cfg.fingers["index"]
    assert metric_to_servo_angle(-100, f) == f.servo_closed_deg
    assert metric_to_servo_angle(100, f) == f.servo_open_deg
    assert metric_to_servo_angle((f.metric_closed + f.metric_open) / 2, f) == pytest.approx(80)
