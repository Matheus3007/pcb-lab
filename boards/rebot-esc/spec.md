# rebot-esc: spec

Status: draft (spec interview) · Owner: Matheus3007 · Assembly tier: see board.yaml
Project context: `docs/projects/battlebot.md`, part research: `docs/projects/battlebot-esc-research.md`

> Every `TBD` that affects layout must be resolved before gate 2.

## Purpose
Plug-in sensorless BLDC drive ESC module for Rebot (3 lb undercutter). One module per drive motor,
two per robot, identical and swappable. Runs stock AM32 firmware (target `OPENESC_20_F421` pin mapping),
takes DShot (bidirectional, extended telemetry) from the carrier board (`rebot-carrier`) and drives one
iFlight Xing 2207 1800 kV motor rewired to wye (~1040 kV).

## Mechanical
- Envelope: rear-right channel of the chassis, one module at each end of the carrier
  (`RebotAssemblyV3.STEP`; channel ≈35 mm deep at the wheel end, 17–20 mm at the centre end).
- Max outline: **≈27.5–30 × 15 mm** (2×10 header ≈25.4 × 5 mm sets the length; the buck adds ~2–3 mm).
- Thickness: 1.0 mm (keeps the stack ≈15 mm; Economic allows 0.8–1.6).
- Parts: **top side only** (SMD); the male header is through-hole, body on the bottom side, pins down
  into the carrier's socket.
- Height: top-side parts ≤ 2 mm (MOSFETs ~1 mm, MCU/driver ~0.8 mm, 1206 caps ~1.6 mm).
- Mounting: one M2 hole in the middle (screw into a standoff on the carrier, no current); must also
  work with Kapton tape only. Keep copper/parts clear of the screw head (≈ Ø4.5 mm).
- Mass budget: ≤ 2 g including header.
- Environment: combat robot, **shock first** (weapon hits, arena slams). No tall or heavy parts,
  no parts on the edges that touch the screw head, keep the MCU/driver away from board flex near the header.

## Electrical
- Layers: 4 (signal / GND / power / signal) · copper: **1 oz**, wide pours for phases/VBAT/GND
- **Self-contained** like an off-the-shelf ESC: only battery + DShot come in (plus SWD for flashing).
  - VBAT: 6S LiHV, 18–26.1 V, regen spikes above that; MOSFETs 60 V, driver 100 V, buck 65 V.
  - DShot signal (3.3 V, bidirectional, open-drain style per AM32).
- Rails on the module: **11 V gate rail** from VBAT via an LMR36506 buck (65 V, 1 MHz, 22 µH);
  **3.3 V** from 11 V via HT7533 (Basic, 100 mA) for the MCU.
- High-current nets: phases A/B/C **20–30 A peak**, low single-digit amps average (drive is
  < 2.5 A battery-side for both motors); VBAT/GND up to ~10 A short peaks.
- Critical signals: gate drive loops (driver → gate → source, short and tight), BEMF divider network
  to the MCU comparator, DShot input.
- Connector: **2×10 2.54 mm male header, through-hole**, hand-soldered; mating 2×10 socket on the
  carrier (2×9 parts researched: HX PZ2.54-2x9P ZZ C42372517 / HC-PM254-8.5H-2x9PZ C22373914). Pinout:
  - Phases A, B, C: 3 pins each (9)
  - VBAT: 3 (pins 1–3) · GND: 4 (4–6, 8) · **KEY: 7** · DShot: 9 · SWDIO: 10 · SWCLK: 11 ·
    A: 12–14 · B: 15–17 · C: 18–20
  - **Mechanically keyed:** pin 7 is pulled out of the module's header and hole 7 of the carrier's
    socket is blocked (a cut pin soldered in). A module rotated 180° can't go in. Electrically a
    rotated module would short the battery through body diodes and a motor winding, so the key is
    required, not optional. The M2 screw hole also only aligns one way.
- Programming: SWDIO/SWCLK on the main header. One-time AM32 bootloader flash with a 2×10 socket jig:
  ST-LINK 5 V → VBAT pins (the buck passes ~4.7 V through in dropout, HT7533 makes 3.3 V), GND, SWDIO, SWCLK.
- Current sense: **none on the module.** The owner doesn't use AM32 current limiting ("rather lose the
  ESC than the fight"); per-motor current is measured on the carrier, in each module's VBAT feed.
  Stock AM32 target (`OPENESC_20_F421`, NO_CURRENT_SENSE) unchanged.

## Parts policy
- Pinned: AT32F421G8U7 (C2765098), DRV8300DRGER (C3655801), 6× HSBB6066 (C2828498),
  LMR36506RRPER (C2870127), FNR3015S 22 µH (C167761), HT7533-1 (C14289, Basic), 10 µF 50 V MLCCs (C440198, Basic).
- Passives: Basic only (`lib/basic_passives.yaml` first). Min package 0402 (Economic).
- Extended parts: unavoidable for MCU, driver, MOSFETs, header (no Basic/Preferred options exist,
  see research notes). Keep everything else Basic.

## Fab
- Quantity: 10 (2–2.5 robots × 2 + spares) · finish: **ENIG** · mask color: **black**
- Assembly: Economic, one side SMD. The through-hole header is **hand-soldered by the owner** (not in the JLC BOM).

## Open questions
- (none open for gate 1)

## Changelog
| Date | Change / gate | Notes |
|---|---|---|
| 2026-10-11 | Scaffolded, spec draft | From the Rebot planning discussion |
| 2026-10-11 | Interview answers | Hand-soldered header, 1 oz, black ENIG |
| 2026-10-11 | Interview closed | SWD on a 2×10 header; current sense moved to the carrier |
| 2026-10-11 | Gate 1 review: items approved, one change pending | OK: header key at pin 7 (GND 4→3), size copper for 5 A continuous, 10 Ω gate resistors, own MOSFET footprint, MCU EP land. Item 5 changed: module made self-contained (owner's call), see next row |
| 2026-10-11 | Self-contained power | LMR36506 65 V buck → 11 V gate rail on the module; carrier's 12 V removed; header pin 8 → GND |
| 2026-10-11 | gate 1 approved | Self-contained power block accepted; on to outline + placement |
