# Verification, reproducibility, and performance

## Tests present

The Python suite validates configuration rejection, normalized landmark geometry, clamped calibration mapping, manual arming, loss-of-tracking behavior, transport faults, and corrupted serial-frame handling. Python CI runs tests, Ruff lint, strict MyPy, and a simulation-only CLI smoke test. Arduino CI is configured to compile the UNO sketch.

**Testing performed here:** automated Python tests and dry-run CLI (see delivery summary). Full GitHub Actions and physical hardware tests are **not** represented as completed until they actually run in the target environment.

## Original project observations

Historical measurements supplied with the original project:

| Original reported result | Interpretation / caveat |
| --- | --- |
| 0.58 s | Mean finger response delay, with no original per-trial timestamps provided |
| 12°–20° | Reported angle difference between the human hand and robotic fingers; measurement apparatus and statistical spread not provided |
| Above 90% “efficiency” | No defined denominator, task success criterion, or confidence interval; **not** asserted here as ML accuracy |

The demonstration video shows physical finger movement following visual human gestures, but alone cannot independently validate those quantitative metrics. No new measured tracking accuracy, hardware latency, torque, or operational lifetime is claimed.

## Proposed reproducible validation procedure

1. Capture timestamps at image acquisition, landmark completion, serial send, Arduino ACK, and physical finger movement (e.g. high-frame-rate camera or encoders).
2. Collect repeated closed/open gesture trials at multiple camera distances and lighting conditions; describe misses and observed jitter.
3. Measure joint deflection and latency distributions, not just the mean; report p50/p95, error bars, and number of trials.
4. Measure loss-of-tracking and USB disconnect behavior, firmware watchdog timeout, physical power cutoff, and re-arming behavior.
5. Run unloaded endurance and thermal/current tests in a guarded environment before considering more substantial use.

These are **future tests**, not verified results.

## Acceptance gate

Software simulation success does not mean the prototype is field-ready. A credible physical prototype report requires verified wiring and independent power cutoff, recorded calibration, firmware compile/upload, protocol interoperability, measured motion, and repeatable failure-mode testing.
