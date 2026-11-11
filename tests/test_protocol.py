import pytest

from robotic_hand.protocol import decode_frame, encode_frame, move_frame


def test_roundtrip():
    frame = decode_frame(encode_frame(42, "MOVE", "50,60,70,80,90"))
    assert (frame.sequence, frame.verb, frame.payload) == (42, "MOVE", "50,60,70,80,90")


def test_checksum_rejects_corruption():
    corrupted = encode_frame(23, "PING").replace(b"PING", b"PONG")
    with pytest.raises(ValueError):
        decode_frame(corrupted)


def test_limits():
    with pytest.raises(ValueError):
        move_frame(1, (20, 60, 70, 80, 90))
    with pytest.raises(ValueError):
        move_frame(1, (60, 60, 70, 80))
    with pytest.raises(ValueError):
        encode_frame(1, "MOVE", "\rINJECT")


def test_rejects_malformed_serial_frames():
    for frame in (b"garbage\n", b"@0001:PING*GG\n", b"@bad:PING*00\n"):
        with pytest.raises(ValueError):
            decode_frame(frame)
