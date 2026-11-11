# Calibration

Calibration parameters are stored in [`config/hand_config.json`](../config/hand_config.json). **Values in that file are illustrative starting points, not measured calibration results for the pictured hand.**

## Landmark measurement

The tracked hand supplies 21 normalized 2D landmarks. The normalization scale is the distance between index MCP (5) and pinky MCP (17). Each finger uses a simple landmark-distance ratio:

| Finger | Tip | Reference |
| --- | --- | --- |
| Thumb | 4 | 17 (pinky MCP) |
| Index | 8 | 0 (wrist) |
| Middle | 12 | 0 (wrist) |
| Ring | 16 | 0 (wrist) |
| Pinky | 20 | 0 (wrist) |

`metric_closed` and `metric_open` define the observed ratios for a curled and extended pose, respectively. A bounded linear interpolation maps the observed ratio onto `servo_closed_deg` and `servo_open_deg` for that finger. Reverse the servo endpoints to reverse direction. This is a pragmatic heuristic and may fail for palm rotation, occlusion, or unusual gestures.

## Calibration data to collect

A useful bench record includes, for **each finger**, observed closed/open hand ratio, observed physical safe servo endpoints, control direction, unloaded mechanical clearance, and repeatability across multiple gestures. These values must be established with a separate low-energy setup before motor activation.

## Control parameters

- `ema_alpha`: position smoothing strength (smaller = smoother/slower).
- `max_command_rate_hz`: upper bound on host command frequency.
- `max_servo_speed_deg_s`: commanded degrees per host elapsed second, independently capped at 14° per command to remain within firmware's 15° cap.
- `deadband_deg`: suppresses very small motion requests.
- `required_stable_frames`: consecutive valid frames before manual arm is permitted.
- `tracking_loss_timeout_s`: maximum gap between valid hand observations before controller stops and requires rearming.

**Warning:** As the system is open-loop, neither physical finger deflection nor actual joint speed can be inferred from servo commands alone. The two quantities need a separate physical measurement protocol.
