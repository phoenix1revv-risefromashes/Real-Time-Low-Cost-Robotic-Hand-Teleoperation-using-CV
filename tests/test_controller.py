from robotic_hand.controller import Controller, State
from robotic_hand.geometry import Point
from robotic_hand.transport import SimulatedActuator


def hand():
    pts = [Point(0.5, 0.5) for _ in range(21)]
    pts[5], pts[17] = Point(0.35, 0.5), Point(0.65, 0.5)
    pts[4], pts[8], pts[12], pts[16], pts[20] = (
        Point(0.3, 0.2), Point(0.42, 0.2), Point(0.5, 0.15), Point(0.58, 0.2), Point(0.7, 0.28)
    )
    return pts


def test_explicit_arm_and_tracking_loss(cfg):
    fake = SimulatedActuator()
    controller = Controller(cfg, fake)
    for i in range(5):
        controller.observe(hand(), i * 0.04)
    assert not fake.commands
    controller.arm(0.17)
    controller.observe(hand(), 0.21)
    assert controller.state == State.ARMED
    assert fake.commands
    assert all(30 <= a <= 130 for angles in fake.commands for a in angles)
    controller.observe(None, 0.60)
    assert controller.state == State.TRACKING_LOST
    assert fake.stops == 1
    controller.observe(hand(), 0.64)
    assert controller.state == State.TRACKING_LOST  # no automatic re-arming


def test_invalid_landmark_triggers_loss(cfg):
    fake = SimulatedActuator()
    controller = Controller(cfg, fake)
    for i in range(5):
        controller.observe(hand(), i * 0.04)
    controller.arm(0.17)
    controller.observe(hand(), 0.20)
    pts = hand()
    pts[8] = Point(1.5, 0)
    controller.observe(pts, 0.60)
    assert controller.state == State.TRACKING_LOST


def test_transport_failure_faults_controller(cfg):
    class FailingActuator(SimulatedActuator):
        def send_angles(self, angles):
            raise OSError("USB disconnected")

    fake = FailingActuator()
    controller = Controller(cfg, fake)
    for i in range(5):
        controller.observe(hand(), i * 0.04)
    controller.arm(0.17)
    controller.observe(hand(), 0.21)
    assert controller.state == State.FAULT
    assert fake.stops == 1


def test_stale_hand_cannot_be_armed(cfg):
    fake = SimulatedActuator()
    controller = Controller(cfg, fake)
    for i in range(5):
        controller.observe(hand(), i * 0.04)
    import pytest

    with pytest.raises(RuntimeError, match="recent"):
        controller.arm(5.0)
    assert controller.state == State.DISARMED
    assert fake.commands == []


def test_large_observation_gap_cannot_bypass_firmware_slew(cfg):
    fake = SimulatedActuator()
    controller = Controller(cfg, fake)
    for i in range(5):
        controller.observe(hand(), i * 0.04)
    controller.arm(0.17)
    controller.observe(hand(), 0.18)
    # Each sent command stays inside the Arduino's 15-degree per-command bound.
    first = fake.commands[-1]
    assert max(abs(angle - 90) for angle in first) <= 15
    controller.observe(hand(), 0.35)
    assert controller.state == State.ARMED
    second = fake.commands[-1]
    assert max(abs(a - b) for a, b in zip(second, first)) <= 15


def test_manual_stop_requires_fresh_frames_and_arm(cfg):
    fake = SimulatedActuator()
    controller = Controller(cfg, fake)
    for i in range(5):
        controller.observe(hand(), i * 0.04)
    controller.arm(0.17)
    controller.observe(hand(), 0.18)
    previous_count = len(fake.commands)
    controller.disarm()
    controller.observe(hand(), 0.2)
    assert len(fake.commands) == previous_count
    assert controller.state == State.DISARMED
