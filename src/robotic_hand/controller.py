"""Explicit arming state machine, fault handling, rate limiting, and smoothing."""

from __future__ import annotations

import math
from collections.abc import Sequence
from enum import StrEnum

from robotic_hand.config import FINGERS, HandConfig
from robotic_hand.geometry import Point, angles_from_landmarks
from robotic_hand.transport import Actuator


class State(StrEnum):
    DISARMED = "DISARMED"
    ARMED = "ARMED"
    TRACKING_LOST = "TRACKING_LOST"
    FAULT = "FAULT"


class Controller:
    """No motion without explicit arm + multiple consecutive valid hand frames."""

    def __init__(self, config: HandConfig, actuator: Actuator) -> None:
        config.validate()
        self.config = config
        self.actuator = actuator
        self.state = State.DISARMED
        self.stable_frames = 0
        self.last_seen: float | None = None
        self.last_sent: float | None = None
        self.last_ping: float | None = None
        # Match the firmware virtual-home setpoint after STOP / reset.
        self._current = {name: 90.0 for name in FINGERS}
        self._filtered: dict[str, float] | None = None
        self.last_fault: str | None = None

    def arm(self, now: float) -> None:
        if self.state == State.FAULT:
            raise RuntimeError(f"Cannot arm while faulted: {self.last_fault}")
        if (
            not math.isfinite(now)
            or self.last_seen is None
            or now < self.last_seen
            or now - self.last_seen >= self.config.tracking_loss_timeout_s
        ):
            raise RuntimeError("No sufficiently recent hand observation for arming")
        if self.stable_frames < self.config.required_stable_frames:
            raise RuntimeError("Hand not yet stable and completely in frame")
        if self.state == State.ARMED:
            return
        self._filtered = None
        self.last_sent = None
        self.last_ping = None
        self.state = State.ARMED

    def disarm(self, state: State = State.DISARMED) -> None:
        self.state = state
        self._filtered = None
        self.stable_frames = 0
        self.last_seen = None
        self.last_sent = None
        self.last_ping = None
        self._current = {name: 90.0 for name in FINGERS}
        # A stop failure is significant; expose it instead of claiming safety.
        try:
            self.actuator.stop()
        except Exception as exc:
            self.state = State.FAULT
            self.last_fault = f"STOP command failed ({exc})"
            raise

    def _fault(self, message: str) -> None:
        self.state = State.FAULT
        self.last_fault = message
        try:
            self.actuator.stop()
        except Exception:
            # Firmware timeout and independent hardware E-stop remain essential.
            pass

    def observe(self, landmarks: Sequence[Point] | None, now: float) -> None:
        """Process one frame; all timestamps are monotonic seconds."""
        if not math.isfinite(now):
            raise ValueError("Invalid timestamp")
        if self.state == State.FAULT:
            return
        try:
            if landmarks is None:
                self.stable_frames = 0
                if (
                    self.state == State.ARMED
                    and self.last_seen is not None
                    and now - self.last_seen >= self.config.tracking_loss_timeout_s
                ):
                    self.disarm(State.TRACKING_LOST)
                return
            desired = angles_from_landmarks(landmarks, self.config.fingers)
        except ValueError:
            self.observe(None, now)
            return

        if self.last_seen is not None and now < self.last_seen:
            self._fault("Monotonic clock moved backward")
            return
        if self.state == State.ARMED and self.last_seen is not None:
            if now - self.last_seen >= self.config.tracking_loss_timeout_s:
                self.disarm(State.TRACKING_LOST)
                return
        self.last_seen = now
        self.stable_frames = min(self.config.required_stable_frames, self.stable_frames + 1)
        if self.state != State.ARMED:
            return

        interval = 1.0 / self.config.max_command_rate_hz
        if self.last_sent is not None and now - self.last_sent < interval:
            return
        dt = interval if self.last_sent is None else max(0.0, now - self.last_sent)
        if self._filtered is None:
            self._filtered = desired.copy()
        else:
            a = self.config.ema_alpha
            self._filtered = {
                name: a * desired[name] + (1 - a) * self._filtered[name]
                for name in FINGERS
            }
        # Firmware independently rejects commands over 15 degrees per frame.
        max_step = min(14.0, self.config.max_servo_speed_deg_s * dt)
        targets: dict[str, float] = {}
        for name in FINGERS:
            delta = self._filtered[name] - self._current[name]
            targets[name] = self._current[name] + min(max_step, max(-max_step, delta))
        any_changed = any(
            abs(targets[name] - self._current[name]) >= self.config.deadband_deg
            for name in FINGERS
        )
        try:
            if any_changed:
                rounded = [int(round(targets[name])) for name in FINGERS]
                # An explicit five-element tuple matches the actuator protocol.
                angles = (rounded[0], rounded[1], rounded[2], rounded[3], rounded[4])
                self.actuator.send_angles(angles)
                self._current.update(targets)
                self.last_sent = now
                self.last_ping = now
            elif self.last_ping is None or now - self.last_ping >= 0.15:
                self.actuator.ping()
                self.last_ping = now
                self.last_sent = now
        except Exception as exc:
            self._fault(str(exc))

    def close(self) -> None:
        try:
            self.disarm()
        finally:
            self.actuator.close()
