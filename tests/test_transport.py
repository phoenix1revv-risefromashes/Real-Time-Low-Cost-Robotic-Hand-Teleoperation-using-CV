import pytest

from robotic_hand.protocol import encode_frame
from robotic_hand.transport import SerialActuator


class StubPort:
    def __init__(self, response: bytes):
        self.response = response
        self.writes = []

    def write(self, data):
        self.writes.append(data)

    def flush(self):
        pass

    def readline(self):
        return self.response


def test_ack_matches_sequence():
    actuator = SerialActuator.__new__(SerialActuator)
    actuator._seq = 0
    actuator._ack_timeout_s = 0.1
    port = StubPort(encode_frame(1, "OK"))
    actuator._serial = port
    actuator.ping()
    assert port.writes[0] == encode_frame(1, "PING")


def test_explicit_firmware_error_is_raised():
    actuator = SerialActuator.__new__(SerialActuator)
    actuator._seq = 0
    actuator._ack_timeout_s = 0.1
    actuator._serial = StubPort(encode_frame(1, "ERR", "ESTOP"))
    with pytest.raises(RuntimeError, match="ESTOP"):
        actuator.send_angles((90, 90, 90, 90, 90))


def test_invalid_servo_angle_never_reaches_serial():
    actuator = SerialActuator.__new__(SerialActuator)
    actuator._seq = 0
    actuator._ack_timeout_s = 0.1
    port = StubPort(encode_frame(1, "OK"))
    actuator._serial = port
    with pytest.raises(ValueError):
        actuator.send_angles((180, 90, 90, 90, 90))
    assert port.writes == []
