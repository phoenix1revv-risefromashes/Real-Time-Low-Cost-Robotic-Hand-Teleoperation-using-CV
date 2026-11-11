# Hardware integration notes (bench prototype)

## Electrical interfaces

| Arduino UNO | Purpose |
| --- | --- |
| D9, D10, D11, D12, D13 | Servo **signal** pins for thumb, index, middle, ring, pinky, respectively |
| D2 | Normally-closed logic interlock contact to GND; broken/open contact disables PWM |
| GND | Signal reference shared with the external servo supply |
| USB serial | Host-to-Arduino control at 115200 baud |

The five servos require a **separately regulated supply** sized for their combined stall current. Do not power all five from the Arduino 5V pin or a laptop USB port. Keep the motor power path fused and install a **hardwired switch that independently disconnects servo power**. The logic interlock on D2 is not a substitute for the switch; it only detaches PWM. A common reference ground is necessary for servo control signals. The historical schematic is included as project evidence, **not** a validated wiring prescription.

## Firmware

Source: [`robotic_hand_controller.ino`](../hardware/firmware/robotic_hand_controller/robotic_hand_controller.ino). Designed for Arduino UNO + standard Arduino `Servo` library. Firmware compile is covered by the CI workflow, but physical electronics validation is not.

```bash
arduino-cli core install arduino:avr
arduino-cli compile --fqbn arduino:avr:uno hardware/firmware/robotic_hand_controller
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno hardware/firmware/robotic_hand_controller
```

The software transport requires this firmware. The original Python script uses **PyFirmata**, a different protocol, and cannot drive this firmware unchanged.

## Mechanical and software constraints

- Servo travel bounds in the config must remain within the firmware limits (30°–130°). Those default limits are conservative example values, **not guaranteed safe for any linkage**.
- Firm motor stops and finger linkages can be damaged well before the Arduino's numerical limits. Mechanical end stops, cable tension, and finger clearances are device-specific.
- All motors may move unexpectedly on first PWM attachment because there is **no servo encoder or homing sensor**; keep the device unloaded and isolated from fingers/hair/clothing during staged validation.
- A sudden USB loss or host crash cannot reliably cut servo power; the watchdog only detaches PWM output.
- Actual emergency-stop architecture, power system, and safe-state design require separate engineering evaluation.

## Hardware verification status

Neither the custom Arduino firmware nor the new communication protocol has been tested against the physical prototype in this delivery. The old demo proves a previous prototype worked with different software. These are distinct engineering claims.
