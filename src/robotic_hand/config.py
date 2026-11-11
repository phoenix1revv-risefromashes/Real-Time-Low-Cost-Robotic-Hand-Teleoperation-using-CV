"""Validated per-finger calibration and safety configuration."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FINGERS = ("thumb", "index", "middle", "ring", "pinky")
PINS = (9, 10, 11, 12, 13)


@dataclass(frozen=True)
class FingerConfig:
    pin: int
    metric_closed: float
    metric_open: float
    servo_closed_deg: int
    servo_open_deg: int

    def validate(self, name: str) -> None:
        if self.pin not in PINS:
            raise ValueError(f"{name}: pin must be one of {PINS}")
        if not all(math.isfinite(x) for x in (self.metric_closed, self.metric_open)):
            raise ValueError(f"{name}: calibration metrics must be finite")
        if not (0 <= self.metric_closed < self.metric_open <= 10):
            raise ValueError(f"{name}: require 0 <= closed metric < open metric <= 10")
        for angle in (self.servo_closed_deg, self.servo_open_deg):
            if type(angle) is not int or not 30 <= angle <= 130:
                raise ValueError(f"{name}: servo endpoints must be integer degrees in [30, 130]")
        if self.servo_closed_deg == self.servo_open_deg:
            raise ValueError(f"{name}: servo endpoints must differ")


@dataclass(frozen=True)
class HandConfig:
    fingers: dict[str, FingerConfig]
    camera_index: int
    camera_width: int
    camera_height: int
    mirror_camera: bool
    max_command_rate_hz: float
    max_servo_speed_deg_s: float
    ema_alpha: float
    deadband_deg: float
    tracking_loss_timeout_s: float
    required_stable_frames: int

    def validate(self) -> None:
        if set(self.fingers) != set(FINGERS):
            raise ValueError(f"Expected exactly these fingers: {FINGERS}")
        if tuple(self.fingers[name].pin for name in FINGERS) != PINS:
            raise ValueError("Pin assignments must match the firmware's 9-13 mapping")
        for name in FINGERS:
            self.fingers[name].validate(name)
        if type(self.camera_index) is not int or self.camera_index < 0:
            raise ValueError("camera_index must be nonnegative integer")
        if any(type(v) is not int or v < 1 for v in (self.camera_width, self.camera_height)):
            raise ValueError("Camera dimensions must be positive integers")
        if type(self.mirror_camera) is not bool:
            raise ValueError("mirror_camera must be boolean")
        bounds = (
            (self.max_command_rate_hz, 1, 30, "max_command_rate_hz"),
            (self.max_servo_speed_deg_s, 1, 240, "max_servo_speed_deg_s"),
            (self.ema_alpha, 0.001, 1, "ema_alpha"),
            (self.deadband_deg, 0, 10, "deadband_deg"),
            (self.tracking_loss_timeout_s, 0.05, 0.4, "tracking_loss_timeout_s"),
        )
        for value, lower, upper, name in bounds:
            if not math.isfinite(value) or not lower <= value <= upper:
                raise ValueError(f"{name} must be finite in [{lower}, {upper}]")
        if not (
            type(self.required_stable_frames) is int
            and 2 <= self.required_stable_frames <= 30
        ):
            raise ValueError("required_stable_frames must be integer in [2, 30]")


def load_config(path: str | Path) -> HandConfig:
    """Load JSON; reject missing/unexpected fields instead of using unsafe fallbacks."""
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = {
        "fingers", "camera_index", "camera_width", "camera_height", "mirror_camera",
        "max_command_rate_hz", "max_servo_speed_deg_s", "ema_alpha", "deadband_deg",
        "tracking_loss_timeout_s", "required_stable_frames",
    }
    if set(data) != expected:
        missing = expected - set(data)
        unexpected = set(data) - expected
        raise ValueError(f"Invalid configuration keys: missing={missing}, unexpected={unexpected}")
    finger_expected = set(FingerConfig.__dataclass_fields__)
    for name, item in data["fingers"].items():
        if set(item) != finger_expected:
            raise ValueError(f"{name}: expected keys {finger_expected}")
    fingers = {name: FingerConfig(**data["fingers"][name]) for name in FINGERS}
    values = {key: value for key, value in data.items() if key != "fingers"}
    config = HandConfig(fingers=fingers, **values)
    config.validate()
    return config
