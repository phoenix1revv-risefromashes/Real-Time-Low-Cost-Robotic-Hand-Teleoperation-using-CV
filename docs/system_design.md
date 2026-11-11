# System design

## Problem and boundary

A camera observes a hand gesture and five servos reproduce approximate finger extension. This is **teleoperation**, not autonomous grasp planning or human joint-angle reconstruction.

### Components

1. **Tracker (`tracker.py`):** MediaPipe Tasks, video mode, one hand, 21 normalized landmarks. The downloadable model is external to the package. The tracker is isolated so the rest of the code needs no OpenCV/MediaPipe imports.
2. **Geometry (`geometry.py`):** finger-tip to wrist/palm-reference Euclidean distances divided by palm width. Invalid observations are rejected before producing setpoints. These measurements are extension proxies, not joint angles.
3. **Calibration (`config.py`):** explicit per-finger closed/open distance ratios and servo endpoints. Ranges are bounded in two places: Python and Arduino.
4. **Controller (`controller.py`):** DISARMED -> ARMED on explicit input after stable hand frames. Missing/invalid/out-of-date tracking transitions to TRACKING_LOST, and transport failures transition to FAULT. Both require a restart or an explicit new arming sequence; there is no auto-rearm after loss.
5. **Actuator (`transport.py`):** simulation for CI and demos, or a serial ACK-checked Arduino backend. Each frame includes a four-digit sequence and XOR check.
6. **Firmware (`robotic_hand_controller.ino`):** rejects malformed commands and out-of-range setpoints; enforces a 15-degree per-command limit; detaches servo PWM on interlock opening, STOP, or a 450 ms command heartbeat timeout.

### State machine

```text
              5 valid frames + explicit 'a'
DISARMED ------------------------------------> ARMED
  ^                                            |   |
  | (manual stop)                             |   | bad USB/ACK
  +--------------------------------------------+   v
                                         TRACKING_LOST / FAULT
                                               |
                                               +-- no auto-rearm
```

A hand observation is considered stale if its timestamp exceeds the tracking-loss timeout. Commands are emitted at up to the configured rate. An EMA smooths the target, and a slew limit bounds change per transmitted frame. The firmware applies an independent **per-command** slew bound; this is not a measured physical velocity limit.

### Protocol

Request examples:

```text
@0042:MOVE:90,90,90,90,90*HH\n
@0043:PING*HH\n
@0044:STOP*HH\n
```

`HH` is the hexadecimal XOR of the bytes between `@` and `*`. Successful ACK: `@0042:OK*HH`. Rejected command: `@0042:ERR:LIMITS*HH`. USB port opening resets an Arduino UNO; host connection performs an initial handshake. Wrong/missing response or timeout produces a controller FAULT. The firmware uses a **different protocol from StandardFirmata**.

### Important limitations

- A camera cannot determine actual servo joint position without physical sensors.
- Unpowered servo motion may invalidate the firmware's virtual home angle. Motor attachment can cause unexpected movement despite commanded slew limits. Physical calibration and mechanical guarding are necessary.
- The serial checksum detects basic accidental corruption; it is **not an authentication or safety-certified transport**.
- The Arduino D2 interlock only disables PWM. A separate physical power cut is needed to disconnect servo energy.
- No threading or realtime guarantee is claimed for Python, OpenCV, MediaPipe, or USB serial transport.
