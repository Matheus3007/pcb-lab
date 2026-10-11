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
- Max outline: **≈25 × 15 mm** (2×9 header ≈23 × 5 mm sets the length).
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
- Layers: 4 (signal / GND / power / signal) · copper: 1 oz outer (2 oz TBD, see open questions)
- Inputs (all from the carrier through the header):
  - VBAT: 6S LiHV, 18–26.1 V, regen spikes above that; MOSFETs and driver rated 60/100 V.
  - 12 V gate supply (GVDD), shared buck on the carrier.
  - DShot signal (3.3 V, bidirectional, open-drain style per AM32).
- Rails on the module: 3.3 V from 12 V via HT7533 (Basic, 100 mA) for the MCU.
- High-current nets: phases A/B/C **20–30 A peak**, low single-digit amps average (drive is
  < 2.5 A battery-side for both motors); VBAT/GND up to ~10 A short peaks.
- Critical signals: gate drive loops (driver → gate → source, short and tight), BEMF divider network
  to the MCU comparator, DShot input.
- Connector: **2×9 2.54 mm male header, through-hole** (e.g. HX PZ2.54-2x9P ZZ, C42372517), mating
  socket on the carrier (e.g. HC-PM254-8.5H-2x9PZ, C22373914). Pinout:
  - Phases A, B, C: 3 pins each (9)
  - VBAT: 3 · GND: 4 · 12 V: 1 · DShot: 1
  - Keyed by placement on the carrier (the module only fits one way; asymmetric pin assignment so a
    180° plug-in can't short VBAT to GND). TBD exact map at gate 1.
- Programming: SWD pads (SWDIO, SWCLK, 3V3, GND) for the one-time AM32 bootloader flash.

## Parts policy
- Pinned: AT32F421G8U7 (C2765098), DRV8300DRGER (C3655801), 6× HSBB6066 (C2828498),
  HT7533-1 (C14289, Basic), 10 µF 50 V MLCCs (C13585 / C440198, Basic).
- Passives: Basic only (`lib/basic_passives.yaml` first). Min package 0402 (Economic).
- Extended parts: unavoidable for MCU, driver, MOSFETs, header (no Basic/Preferred options exist,
  see research notes). Keep everything else Basic.

## Fab
- Quantity: 10 (2–2.5 robots × 2 + spares) · finish: TBD · mask color: TBD
- Assembly: Economic, one side. Header: TBD (JLC through-hole assembly or hand-soldered).

## Open questions
- Header soldering: JLC through-hole assembly (extra fee) or hand-soldered by the owner?
- First flash: does the owner have an ST-LINK? SWD as test pads (pogo jig / hold-down) or a tiny
  header footprint?
- Per-module current sense (shunt + amplifier on PA3 → per-motor current in telemetry), or
  carrier-level only?
- Copper weight: 1 oz (cheaper) vs 2 oz outer (phase current peaks).
- Finish / mask color.

## Changelog
| Date | Change / gate | Notes |
|---|---|---|
| 2026-10-11 | Scaffolded, spec draft | From the Rebot planning discussion |
