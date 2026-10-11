# <board name>: spec

Status: draft · Owner: <human> · Assembly tier: see board.yaml

> Fill with the human. Every `TBD` that affects layout must be resolved before gate 2.
> This file is the single source for constraints; YAML/py files reference it.

## Purpose
What the board does, in 2–3 sentences.

## Mechanical
- Envelope / chassis files: `mechanical/chassis/…` (STEP preferred; SVG/DXF for 2D)
- Max outline: TBD × TBD mm, cutouts: TBD
- Thickness: TBD mm (JLC options: 0.4/0.6/0.8/1.0/1.2/1.6/2.0)
- Height limits per side / region: TBD
- Mounting: TBD (holes, standoffs, adhesive, potting?)
- Mass budget: TBD g
- Environment: shock/vibration, temperature, moisture: TBD

## Electrical
- Layers: TBD · copper weight: TBD oz
- Power inputs (voltage range, source, reverse polarity?): TBD
- Rails and max currents: TBD
- High-current nets (A continuous / peak): TBD
- Critical signals (USB, SPI to IMU, current sense, PWM): TBD
- Connectors (type, pinout, mating part): TBD

## Parts policy
- Must-use / pinned parts (LCSC IDs): TBD
- Min package size: TBD (Economic: ≥0402)
- Allowed: Extended parts? max count: TBD

## Fab
- Quantity: TBD · surface finish: TBD · solder mask color: TBD
- Panelization: TBD (required for Standard tier if < 70×70 mm)

## Open questions
- …

## Changelog
| Date | Change / gate | Notes |
|---|---|---|
