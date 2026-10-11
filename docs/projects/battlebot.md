# Project: 3 lb battlebot integrated board

Context only, not yet a spec. Turn into `boards/bot-main/spec.md` with the human once Phase 0 is done.

## Known so far (2026-10-11)
- Integrated, modular main board for a 3 lb (beetleweight) combat robot.
- STM32 **F or G series** MCU + **IMU** for closed-loop control.
- Possibly **current sensing** per motor for sensorless odometry estimates.
- Must fit a specific chassis (human will supply 3D/SVG). Expect unconventional outline
  and cutouts. **Very small, very light, shock-resilient.**
- Two drive motors + weapon motor.

## Open decisions
- ESCs: off-the-shelf AM32 boards vs onboard AM32-style ESCs vs a micro-VESC-style FOC design
  for drive and/or weapon. Needs a trade study (size, mass, current, thermal, firmware effort,
  BOM cost, JLC part availability for MOSFETs/gate drivers).
- Receiver interface (protocol, connector), battery (cell count, connector), power switch/link.
- Layer count and copper weight (driven by motor currents).
- Assembly tier: likely forced to **Standard + panel** if two-sided on a sub-70 mm board.

## Design considerations to carry into the spec
- Shock: avoid tall/heavy unsupported parts, prefer small packages, strain relief on wires,
  no parts at the impact-facing edges, consider conformal coating.
- IMU: place near the centre of rotation, away from motor current paths, rigidly mounted.
- Current sense: Kelvin connections, sense routing away from switching nodes.
- Thermal: high-current paths sized from IPC-2152 for short-duration peaks.
