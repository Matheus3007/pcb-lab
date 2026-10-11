# rebot-ctrl: spec

Status: in progress (all gates pre-approved by the owner, 2026-10-11) · Owner: Matheus3007 · Assembly tier: see board.yaml
Project context: `docs/projects/battlebot.md` (Plan).

## Purpose
Mini controller for Rebot (3 lb undercutter). Sits between the ELRS receiver and an off-the-shelf 4-in-1
AM32 ESC (Flywoo GOKU G45M): CRSF in, DShot (bidirectional) out to left drive / right drive / weapon
(+ one spare channel), gyro turn-rate control, fight logging, USB for logs/config/firmware. Powers the
receiver from its own 65 V-rated buck (fixes the BEC that ran over its 26 V rating on 6S LiHV).

## Mechanical
- Taped onto the (isolated) G45M, the stack taped to the chassis: must fit inside the G45M outline
  (33 × 30 mm). **Outline 30 × 28 mm** (gate 2). The stack stands in the rear channel (≈31 mm free height).
- Parts on the top side only (Economic). Connectors on the edges, mouths outward.
- Mass target ≈ 2–2.5 g. No mounting holes (taped). Rigid in rotation for the gyro (tape is fine).
- Environment: combat robot, shock first: small packages, no tall parts, connectors with locking/MP pads.

## Electrical
- Layers: 4 · copper 1 oz · thickness 1.0 mm.
- Input: VBAT 6S LiHV 18–26.1 V (+ braking spikes) from the ESC connector's V pin. USB VBUS 5 V for the bench.
- Rails: +5V (LMR36506 buck set to 5.55 V, then a Schottky OR with USB VBUS ≈ 5.2 V) for the receiver
  (~150–300 mA) and the LDO; 3V3 (XC6206, 200 mA) for MCU, IMU, flash.
- Connectors:
  - **J1 ESC, JST-SH 8P (SM08B-SRSS-TB)**, same order as the G45M silkscreen "G V 1 2 3 4 C T", straight
    cable: 1 GND, 2 VBAT, 3 M1, 4 M2, 5 M3, 6 M4, 7 CURR (ESC current sensor), 8 TLM (ESC serial telemetry).
    Not published by Flywoo: **check G and V on the ESC with a multimeter before the first plug-in.**
    A reversed cable is survivable: VBAT could only reach the CURR input, which has a 100k/10k divider.
  - **J2 receiver, JST-GH 4P (SM04B-GHS-TB)**: 1 +5V, 2 GND, 3 RX_TX (receiver TX → MCU RX), 4 RX_RX (MCU TX → receiver RX). CRSF.
  - **J3 USB-C (HRO TYPE-C-31-M-12)**: USB 2.0 device (PA11/PA12), 5.1k CC sink, VBUS ORed into +5V.
  - SWD/boot test pads: 3V3, GND, SWDIO, SWCLK, NRST, BOOT0.
- MCU STM32G431CBU6; IMU LSM6DSV32X (SPI1); flash W25Q128JV 16 MB (SPI1). Pin map in circuit.py.
- No Bluetooth (owner, 2026-10-11).

## Parts policy
- Basic passives (0402); Extended only where no Basic exists (MCU, IMU, flash, buck, inductor, connectors).

## Fab
- Quantity 5 · ENIG · black mask · Economic assembly, one side.

## Open questions
- (none: gates pre-approved)

## Changelog
| Date | Change / gate | Notes |
|---|---|---|
| 2026-10-11 | Scaffolded + spec | From the Rebot plan; gates pre-approved by the owner |
| 2026-10-11 | gate 1 (pre-approved) | 12 assertions pass, ERC clean (3 datasheet tie-offs waived), 209 pins match; USB diode D2 in SOD-323 (B5819WS) |
| 2026-10-11 | gate 2 (pre-approved) | 30 × 28 mm: USB-C + ESC JST-SH on the top edge, receiver JST-GH left, MCU centre (rot 180), flash right, IMU bottom, buck/LDO bottom left, SWD pads bottom right; 26 rules |
