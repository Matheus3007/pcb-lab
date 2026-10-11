# Project: 3 lb battlebot integrated board ("Rebot")

Context only, not yet a spec. Turn into `boards/<name>/spec.md` with the human once Phase 0 is done.

## The robot (2026-10-11)
- Rebot: 3 lb (beetleweight) undercutter, ~23 cm bar, exactly at weight limit. Robocore/LBR rules
  (Brazil): no tip-speed or battery limits beyond LiPo/LiHV.
- CAD: `C:\Users\mathe\Documents\pendriveBackup\rebot\RebotV3\RebotAssemblyV3.STEP` (SolidWorks,
  no electronics in it), chassis `RebotV3/Chassis/ChevronChassisV5.STEP`. Rough electronics
  dimensions in `rebot/equations.txt`. Electronics sit in the chevron chassis around the weapon
  pulley: battery left-centre, ESC strips along the walls.
- Battery: Gaoneng GNB 6S LiHV 650 mAh 120C, XT30. **Max 26.1 V** (4.35 V/cell) before spikes.
- Drive: 2× iFlight Xing 2207 1800 kV rewired delta→wye (÷√3 kV). Both drives together < 2.5 A
  (measured, battery side). Tangential drive.
- Weapon: iFlight 2814 800 kV rewired to **wye** (~460 kV, ~12k rpm unloaded). Tangential
  ratchet-TPU / Vytaflex wheel drive. Speed is not the goal; energy is in the heavy bar.
- ESCs today: DYS Aria 70A (weapon), 2× B-CUBE AM32 45A (drive). All AM32, all reliable.
- Receiver: generic ELRS 3.2 7-ch PWM receiver (supports CRSF), fed by a generic 5 V 3 A mini BEC
  rated **7–26 V input**.
- Whole current electronics bundle (ESCs, wiring, connectors, RX, BEC): **64 g**. The board
  (with everything it replaces) must not exceed that.

## Problems to solve
1. Receiver drops out sporadically, **also on the bench with only the drives running**.
   Leading hypothesis: the BEC is at/over its 26 V input rating on a full LiHV pack (26.1 V), and
   drive braking/reversal pumps the bus higher. Bench test to confirm: storage-charged pack
   vs freshly charged, or RX powered from a separate 5 V source.
2. Cable management in a cramped chassis.
3. XT30s in the power bus physically disconnect (a fight was lost to the weapon ESC unplugging).

## Decisions so far
- Battery is **never** soldered to the board. Board has PTH pads for **two pigtails**: the battery
  XT30 lead, and an independent power-link lead that stays open until a shorted XT30 female is
  plugged in before the fight (the robot's power switch today). Onboard kill switch: later.
- Off-board ESCs attach by soldered wires/pads, swappable in **< 5 min per ESC**. Signals on locking
  connectors (JST-GH style).
- **v1 board:** controller + power + **onboard AM32 drive ESCs**; the weapon stays on the Aria.
  **v2:** onboard weapon ESC, only after v1 drive ESCs prove out, preceded by a deep open-source
  ESC research pass. Each order cycle should cost **< R$600 all-inclusive** (shipping + import tax) delivered to Brazil.
- Weapon current path sized for **40 A** (35 A acceptable if space/weight demands).
- **Carrier MCU: STM32G431CBT6** (LQFP-48 7×7, C529355), locked 2026-10-11. Same G4 family as the
  Team-Micras v0 board (STM32G474), so their CubeMX/CMake setup and `micras_core`/`micras_hal` carry
  over (https://github.com/Team-Micras/MicrasFirmware). **IMU: LSM6DSV32X** (C22461202), ±32 g /
  ±4000 °/s, same family as their LSM6DSV driver. BLE: their HM-19 module + `micras_comm` link.
- Receiver → MCU via CRSF; MCU → ESCs via DShot (bidirectional for eRPM).
- Firmware wanted: gyro-assisted driving, closed-loop wheel speed, weapon RPM, telemetry back to
  the radio over ELRS, fight logs to onboard flash downloaded over USB-C. Firmware lives outside
  the PCB pipeline. Auto control inversion when flipped: not wanted for now.
- Bluetooth: optional plug-in module on a UART header.
- MCU crash or link loss must stop DShot so all ESCs disarm (watchdog, weapon-off failsafe).

## Architecture: carrier + plug-in ESC modules (decided 2026-10-11)
- **Carrier** (~78 × 30 mm, vertical on the rear wall): MCU, IMU, power, logging, USB-C, bulk
  capacitance, and **every wire** in the robot soldered to it (battery + link pigtails, receiver,
  Aria, all motor phases).
- **Drive-ESC modules** (~25 × 15 mm, identical, ~1–2 g): AM32 MCU + gate driver + small MOSFETs,
  no wires and no bulk cap. They plug into the carrier's inner face through **one 2×9 2.54 mm
  through-hole header** (phases, battery, GND, 12 V, DShot), retained by one M2 screw (preferred) or
  Kapton tape alone. A swap is pull and push, no soldering. See `battlebot-esc-research.md`.
- **Sizing:** the 2.5 A drive figure is battery-side. At low duty (stall against a wall) the phase
  current can be several times that, so modules are designed for **20–30 A peak phase current**
  with the AM32 current limit set to match. Three header pins per phase.
- **Fallback:** an adapter module with pads for an off-the-shelf ESC (e.g. BCube).
- **v2 weapon ESC:** a larger module of the same kind, connection sized for its current.
- Stack ≈ 15 mm, so the modules sit at the two ends of the channel (deep enough), one per end,
  rotated 180° from each other so each faces its own motor.
- Only the controller section is non-modular: carry a spare carrier per event.

## Board location (measured from RebotAssemblyV3.STEP, 2026-10-11)
STEP frame: z up (floor top z=2, lid underside z=37.5), x forward (chevron tip x=0), y lateral;
y<0 is the user's "right" side (weapon motor side). The space under the lid is too shallow, so the
board goes in the **rear-right channel** where the weapon ESC and one drive ESC sit now: between
the inner rear wall and the weapon pulley/motor boss. The inner rear wall face runs straight from
(x -119.7, y -87) to (x -103.5, y -6), so the channel is ~81 mm long. Depth from the wall to the
nearest obstacle: ~35 mm at y -75, **13–15 mm at the waist (y -42)**, ~18 mm at y -20, ~20 mm at y -8.
Height 35.5 mm floor to lid.
- Flat on the floor: odd boomerang outline, only ~1700 mm² on one face. Too small.
- **Vertical against the rear wall** (like the ESCs today): ~78 × 30 mm rectangle, both faces
  usable; inner-face parts ≤ ~10 mm tall at the waist, back face low-profile against a soft pad.
  Weapon ESC fits in the deep end (y -60…-85). **Chosen** (2026-10-11). The rear wall is rarely
  hit (once, by a vert's victim landing on the lid), but mount it on soft TPU clips/pads anyway.

## Open
- Drive ESC reference design: which AM32 target to clone (MCU, gate driver, FETs ≥ 40 V, 60 V preferred).
- Layer count, copper weight, assembly tier (likely < 70 mm → Standard + panel if two-sided).
- Cost per order cycle incl. shipping and Brazilian import tax.

## Design considerations to carry into the spec
- Shock: avoid tall/heavy unsupported parts, prefer small packages, strain relief on wires,
  no parts at the impact-facing edges, consider conformal coating.
- IMU: near the centre of rotation, away from motor current paths, rigidly mounted; accel ≥ ±32 g,
  gyro up to ±4000 °/s.
- Current sense: Kelvin connections, sense routing away from switching nodes.
- Thermal: high-current paths sized from IPC-2152 for short-duration peaks.
- Input protection: TVS + bulk capacitance; regulators rated well above 26.1 V (≥ 40–60 V).
