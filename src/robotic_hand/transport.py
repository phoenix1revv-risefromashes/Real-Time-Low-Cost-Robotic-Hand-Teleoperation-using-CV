"""Actuation backends: explicit simulation or checksummed Arduino serial transport."""

from __future__ import annotations

import time
from typing import Protocol

from robotic_hand.protocol import decode_frame, encode_frame, move_frame


class Actuator(Protocol):
    def send_angles(self, angles: tuple[int, int, int, int, int]) -> None: ...

    def ping(self) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


class SimulatedActuator:
    """Fake actuator; useful for tests, dry runs, and camera demonstrations."""

    def __init__(self) -> None:
        self.commands: list[tuple[int, int, int, int, int]] = []
        self.pings = 0
        self.stops = 0
        self.closed = False

    def send_angles(self, angles: tuple[int, int, int, int, int]) -> None:
        self.commands.append(angles)

    def ping(self) -> None:
        self.pings += 1

    def stop(self) -> None:
        self.stops += 1

    def close(self) -> None:
        self.closed = True


class SerialActuator:
    """ACK-checked communication with the custom Arduino firmware.

    Do not use against the original StandardFirmata firmware; it speaks a
    different protocol. The firmware requires normally-closed E-stop wiring.
    """

    def __init__(self, port: str, baudrate: int = 115200, ack_timeout_s: float = 0.12) -> None:
        if not port:
            raise ValueError("An explicit serial port is required")
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("Install with: pip install -e '.[hardware]'") from exc
        self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=0.03, write_timeout=0.1)
        self._seq = 0
        self._ack_timeout_s = ack_timeout_s
        try:
            time.sleep(2.0)  # Arduino UNO resets on opening serial USB.
            self._serial.reset_input_buffer()
            self.ping()
        except BaseException:
            self._serial.close()
            raise

    def _exchange(self, verb: str, payload: str = "") -> None:
        self._seq = (self._seq + 1) % 10000
        data = encode_frame(self._seq, verb, payload)
        self._serial.write(data)
        self._serial.flush()
        deadline = time.monotonic() + self._ack_timeout_s
        while time.monotonic() < deadline:
            response = self._serial.readline()
            if not response:
                continue
            try:
                frame = decode_frame(response)
            except ValueError:
                continue  # discard malformed or stale serial text
            if frame.sequence != self._seq:
                continue
            if frame.verb == "ERR":
                raise RuntimeError(f"Arduino rejected {verb}: {frame.payload}")
            if frame.verb != "OK":
                raise RuntimeError(f"Unexpected Arduino response: {frame.verb}")
            return
        raise TimeoutError(f"No Arduino ACK for {verb}; hardware state unknown")

    def send_angles(self, angles: tuple[int, int, int, int, int]) -> None:
        # Reuse all payload validation from the shared encoder.
        frame = move_frame(0, angles)
        body = decode_frame(frame).payload
        self._exchange("MOVE", body)

    def ping(self) -> None:
        self._exchange("PING")

    def stop(self) -> None:
        self._exchange("STOP")

    def close(self) -> None:
        self._serial.close()
