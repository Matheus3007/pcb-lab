# pipeline-demo: spec

Status: Phase 0 reference board, **not for ordering** · Assembly tier: economic (board.yaml)

## Purpose
Exercise every pipeline stage on a trivial circuit: USB-C 5 V sink → XC6206 3.3 V LDO →
red status LED, plus an unpopulated 4-pin header (VBUS, 3V3, GND, GND).

## Mechanical
- 30 × 24 mm, 2 mm corner radius, R4 semicircular notch on the right edge, 2 × 9 mm internal slot.
- One M2 mounting hole. 1.6 mm FR-4, 2 layers, 1 oz.

## Electrical
- VBUS 5 V from USB-C (CC1/CC2 5.1 k Rd pull-downs, sink only, no data).
- 3V3 up to 100 mA budget (LDO dissipation assertion), LED ≈ 1–1.5 mA.

## Open questions
- none (throwaway)

## Changelog
| Date | Change / gate | Notes |
|---|---|---|
| 2026-10-11 | created; pipeline passes all checks | gates 1–3 packets generated for owner review |
| 2026-10-11 | JLC preview, 4 rounds | Gerbers OK; fixed the shared origin, removed drill maps; CPL corrections confirmed: HRO USB-C 0° + 1.575 mm, SOT-23 180°; D1 polarity OK |
| 2026-10-11 | gates 1–3 passed by owner (via JLC preview) | pipeline proven end to end; not ordered |
