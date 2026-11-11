"""Checksummed newline-delimited serial frames shared with Arduino firmware.

Format: @0123:MOVE:50,60,70,80,90*AB\n, where AB is XOR of bytes
between @ and *. Responses use OK or ERR:CODE instead of MOVE.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Frame:
    sequence: int
    verb: str
    payload: str = ""


def checksum(body: str) -> int:
    if not body.isascii():
        raise ValueError("Only ASCII protocol messages are supported")
    result = 0
    for value in body.encode("ascii"):
        result ^= value
    return result


def encode_frame(sequence: int, verb: str, payload: str = "") -> bytes:
    if not (0 <= sequence <= 9999):
        raise ValueError("sequence must be 0..9999")
    if not verb.isupper() or not verb.isalpha() or len(verb) > 12:
        raise ValueError("Invalid verb")
    if any(character in payload for character in "@*\r\n") or not payload.isascii():
        raise ValueError("Invalid payload")
    body = f"{sequence:04d}:{verb}" + (f":{payload}" if payload else "")
    message = f"@{body}*{checksum(body):02X}\n"
    if len(message) > 96:
        raise ValueError("Frame too long")
    return message.encode("ascii")


def decode_frame(data: bytes) -> Frame:
    try:
        text = data.decode("ascii").strip("\r\n")
        if not text.startswith("@") or text.count("*") != 1:
            raise ValueError("Missing frame delimiter")
        body, claimed = text[1:].rsplit("*", 1)
        if len(claimed) != 2 or int(claimed, 16) != checksum(body):
            raise ValueError("Invalid frame checksum")
        parts = body.split(":", 2)
        if len(parts) < 2 or len(parts[0]) != 4 or not parts[0].isdigit():
            raise ValueError("Invalid sequence number")
        verb = parts[1]
        if not verb.isupper() or not verb.isalpha():
            raise ValueError("Invalid verb")
        return Frame(int(parts[0]), verb, parts[2] if len(parts) == 3 else "")
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("Malformed serial frame") from exc


def move_frame(sequence: int, angles: tuple[int, ...]) -> bytes:
    if len(angles) != 5 or any(not isinstance(x, int) or isinstance(x, bool) or not 30 <= x <= 130 for x in angles):
        raise ValueError("Expected five integer angles in [30, 130]")
    return encode_frame(sequence, "MOVE", ",".join(map(str, angles)))
