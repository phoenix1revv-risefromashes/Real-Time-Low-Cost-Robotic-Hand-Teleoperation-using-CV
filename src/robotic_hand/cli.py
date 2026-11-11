"""Live camera UI, explicit arm/disarm controls, and hardware-free smoke test."""

from __future__ import annotations

import argparse
import logging
import sys
import time

from robotic_hand.config import load_config
from robotic_hand.controller import Controller, State
from robotic_hand.geometry import Point
from robotic_hand.transport import SerialActuator, SimulatedActuator

LOG = logging.getLogger(__name__)


def demo(config_path: str) -> int:
    """Deterministic hardware-free smoke test; no camera required."""
    config = load_config(config_path)
    fake = SimulatedActuator()
    controller = Controller(config, fake)
    points = [Point(0.5, 0.5) for _ in range(21)]
    points[5] = Point(0.35, 0.5)
    points[17] = Point(0.65, 0.5)
    for idx, tip in enumerate((4, 8, 12, 16, 20)):
        points[tip] = Point(0.42 + idx * 0.04, 0.2)
    for i in range(config.required_stable_frames):
        controller.observe(points, i * 0.1)
    controller.arm(0.41)
    for i in range(10):
        controller.observe(points, 0.42 + i * 0.08)
    controller.close()
    print(f"DEMO OK: {len(fake.commands)} simulated movement commands; STOP={fake.stops}")
    return 0


def camera(config_path: str, model: str, port: str | None, hardware: bool) -> int:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV missing; install with pip install -e '.[vision]'") from exc
    from robotic_hand.tracker import HandTracker

    cfg = load_config(config_path)
    if hardware != (port is not None):
        raise ValueError("Hardware operation requires BOTH --enable-hardware and --port")
    actuator = SerialActuator(port) if hardware and port else SimulatedActuator()
    controller = Controller(cfg, actuator)
    capture = None
    tracker = None
    try:
        tracker = HandTracker(model)
        capture = cv2.VideoCapture(cfg.camera_index)
        if not capture.isOpened():
            raise RuntimeError(f"Cannot open camera index {cfg.camera_index}")
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.camera_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.camera_height)
        start_ns = time.monotonic_ns()
        print("Controls: [a] arm after 5 valid frames; [s] stop; [q] quit")
        while True:
            success, frame = capture.read()
            if not success or frame is None:
                raise RuntimeError("Camera read failed: no servo motion is permitted")
            if cfg.mirror_camera:
                frame = cv2.flip(frame, 1)
            now = time.monotonic()
            timestamp_ms = (time.monotonic_ns() - start_ns) // 1_000_000
            points = tracker.detect(frame, timestamp_ms)
            controller.observe(points, now)
            if controller.state == State.FAULT:
                raise RuntimeError(f"Motion control fault: {controller.last_fault}")
            status = (
                f"{controller.state.value} | hand={'YES' if points else 'NO'} "
                "| a ARM / s STOP / q QUIT"
            )
            cv2.putText(frame, status, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (255, 255, 255), 2)
            if points:
                height, width = frame.shape[:2]
                for p in points:
                    cv2.circle(frame, (int(p.x * width), int(p.y * height)), 3, (0, 220, 0), -1)
            cv2.imshow("Vision-guided robotic hand (explicit arm required)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("s"):
                controller.disarm()
            if key == ord("a"):
                try:
                    controller.arm(now)
                    LOG.info("Manual arm accepted")
                except RuntimeError as exc:
                    LOG.warning("Arm rejected: %s", exc)
        return 0
    finally:
        try:
            controller.close()
        finally:
            if tracker is not None:
                tracker.close()
            if capture is not None:
                capture.release()
            cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description="Vision-guided robotic hand controller")
    parser.add_argument("--config", default="config/hand_config.json")
    parser.add_argument("--mode", choices=["demo", "camera"], default="demo")
    parser.add_argument("--model", default="models/hand_landmarker.task")
    parser.add_argument("--enable-hardware", action="store_true", help="Allow physical motors")
    parser.add_argument("--port", help="Serial port, e.g. /dev/ttyACM0 or /dev/cu.usbmodem101")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.mode == "demo":
            if args.enable_hardware or args.port:
                parser.error("Demo mode never enables hardware")
            result = demo(args.config)
        else:
            result = camera(args.config, args.model, args.port, args.enable_hardware)
    except (OSError, RuntimeError, ValueError) as exc:
        LOG.error("%s", exc)
        result = 1
    sys.exit(result)
