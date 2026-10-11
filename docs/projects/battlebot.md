# Project: Rebot electronics (3 lb battlebot)

Current plan first; superseded plans are kept under "History" with the reason they changed.

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

## Plan (decided 2026-10-11, driven by weight: the bot is at the 1360 g limit)
**Off-the-shelf power, our own tiny controller.**

- **ESCs: one Flywoo GOKU G45M 4-in-1** (AM32, 45 A per channel / 50 A 10 s peak, 3–6S, 33 × 30 ×
  6.1 mm, 6.4 g) replaces the Aria + 2 B-CUBEs. Channels: left drive, right drive, weapon, one spare.
  Bought from the FLYWOO Official Store on AliExpress. Notes:
  - 6S-rated (like the B-CUBEs): add a low-ESR ~35 V capacitor on its battery pads for weapon braking spikes.
  - Fits standing in the rear channel (30 mm tall of ~31 mm free, z 6 to 37 from the CAD): solder the
    edge-facing wires flat along the board face. It is stood up where the Aria and a drive ESC were.
  - ESC power leads soldered straight to the battery pigtail: **no XT30s inside the bot** (problem 3).
- **Controller: our own board, `boards/rebot-ctrl`** (to be started with /new-board). Only what the
  4-in-1 can't do:
  - **STM32G431** (G4, same family as Team-Micras v0, reuse `micras_hal/core/comm`) + **LSM6DSV32X**
    IMU (gyro used for heading/turn-rate control; accelerometer not relied on).
  - **8-pin JST-SH ESC connector**, standard 4-in-1 pinout as on the G45M (GND, VBAT, M1–M4, CURR,
    TLM): VBAT in, DShot out (bidirectional for eRPM), ESC current-sensor input for logging.
  - **Own power: 65 V LMR36506 buck → 5 V** (also powers the receiver, replacing the 7–26 V BEC:
    problem 1), LDO → 3.3 V.
  - **Receiver: locking JST-GH** (5 V, GND, CRSF TX/RX).
  - **Log flash: yes** (whole fight: currents, gyro, sticks, RPM, link quality).
  - **USB-C on board, doubling as the BLE port** (owner, 2026-10-11: pads are a hassle in a rushed pit;
    copy the Micras trick). Micras routes USB-C D-/D+ to PA11/PA12, which are a UART on their H7. On
    the **G431, PA11/PA12 can only be USB** (DS12589 table 12: no USART RX/TX there), so D-/D+ go to
    **both** USB (PA11 DM / PA12 DP) **and a spare USART in parallel**. Same mapping as Micras's
    HM-19 dongle: D- = dongle TX -> MCU RX, D+ = MCU TX; **SBU1/SBU2 = 3.3 V through a ~300 mA
    resettable fuse** to power the dongle; CC1/CC2 5.1 k to GND. **VBUS** is sensed to pick the mode
    (cable = USB device: logs, config, DFU flashing; no VBUS = UART for the dongle) and ORed into the
    5 V rail so the board runs from USB on the bench. Connector: HRO TYPE-C-31-M-12 (already verified
    in pipeline-demo). Replaces the USB pads and the separate HM-19 header. SWD pads stay for recovery.
  - Target ~15 × 20 mm, ~2–2.5 g with the USB-C. Must fit inside the G45M outline (33 × 30 mm).
  - **Mounting:** taped to the 4-in-1 (which is isolated), the stack taped to the chassis. The gyro
    needs the board to be rigid in rotation relative to the chassis; foam/tape is fine.
- Firmware: CRSF in, DShot out, gyro turn-rate loop (driving), weapon passthrough, logging, ELRS
  telemetry, BLE link. MCU crash or link loss must stop DShot so the ESC disarms (watchdog,
  weapon-off failsafe). Firmware lives outside the PCB pipeline.
- Off-the-shelf fallback for the controller if needed: Flywoo GOKU H743 Pro Mini + ArduPilot Rover
  (ACRO, gyro-only, Lua), 5.8 g.
- Each order should stay < R$600 all-inclusive (shipping + import tax) to Brazil.

## Weight
- Today's electronics bundle (3 ESCs, wiring, connectors, RX, BEC): 64 g.
- New: G45M 6.4 g + controller ~2 g + short leads. Owner to weigh the old parts to confirm savings.

## Chassis measurements (from RebotAssemblyV3.STEP, 2026-10-11)
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

- Rear channel height free of obstacles: about **31 mm** (chassis floor z ≈ 6 to lid z ≈ 37) where the
  Aria and the stacked drive ESC sit (measured again for the 4-in-1 fit).

## Design considerations to carry into the spec
- Shock: avoid tall/heavy unsupported parts, prefer small packages, strain relief on wires,
  no parts at the impact-facing edges, consider conformal coating.
- IMU: near the centre of rotation, away from motor current paths, rigidly mounted; accel ≥ ±32 g,
  gyro up to ±4000 °/s.
- Current sense: Kelvin connections, sense routing away from switching nodes.
- Thermal: high-current paths sized from IPC-2152 for short-duration peaks.
- Input protection: TVS + bulk capacitance; regulators rated well above 26.1 V (≥ 40–60 V).

## History (superseded, kept for the reasoning)
1. **Carrier + onboard drive ESCs, weapon on the Aria** (first plan). Then **carrier + plug-in
   custom ESC modules** (`boards/rebot-esc`): modules passed gate 1 (AT32F421 + DRV8300D + 6× HSBB6066,
   self-contained 11 V buck, keyed header) and reached gate 2 (36 × 20 mm, B-CUBE-style rows), not approved.
   **Parked** because a one-sided custom module came out no smaller than a B-CUBE, the carrier plus
   modules weighed more than an off-the-shelf 4-in-1, and the weight limit made that decisive. Kept in
   the repo for a possible future all-in-one board. Research: `battlebot-esc-research.md`.
2. Decisions from that phase that still hold: STM32G431 + LSM6DSV32X, CRSF in / DShot out, current
   sensing not on ESCs, battery never soldered to a board, firmware wanted (see Plan).
3. Superseded details (carrier pigtails, 78 × 30 mm vertical carrier, per-ESC current shunts,
   40 A weapon path on the carrier) are in git history before this commit.
