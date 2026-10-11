# Battlebot drive-ESC module: research notes

Started 2026-10-11. Feeds the drive-ESC module spec (see `battlebot.md`, "Architecture").

## Reference design: incutec OpenESC-20x20

- https://github.com/incutec-hw/OpenESC_20X20 (rev3.3, 2026-08-25; checked at commit 4ba8244).
  KiCad 10, OSHWA-certified, built for JLC assembly, 15+ validated units.
- 4-in-1 drone ESC, **one independent channel per motor**, which is exactly our module:
  AT32F421G8U7 MCU → NSG2065Q 3-phase gate driver → 6 MOSFETs (one per switch).
  Power: LMR54406 buck to +10 V (gate drive), TLV76733 LDO to +3V3.
- Firmware: AM32 upstream target **`OPENESC_20_F421`** (`HARDWARE_GROUP_AT_B` + `AT_045`).
  If we keep the same MCU pin mapping, **stock AM32 runs unmodified**. Bidirectional DShot and
  extended DShot telemetry (eRPM, etc.) on the signal line.
  - AT_B pins: input/DShot PB4 (TMR3 CH1); phase A low PB1 / high PA10; B low PB0 / high PA9;
    C low PA7 / high PA8. AT_045 reserves PA3 = current ADC, PA6 = voltage ADC (the OpenESC target
    disables both; a custom target can enable per-module voltage/current telemetry).
- First flash needs SWD (ST-LINK) for the AM32 bootloader. After that, updates and settings go over
  the signal wire (4-way interface): the carrier MCU should implement the passthrough over USB.
- **License: CERN-OHL-S-2.0** (strongly reciprocal). If our module is derived from their sources and
  we distribute it, its sources must be published under the same license. The module will get its
  own LICENSE file in its board folder. Fine for our use; the rest of the repo stays MIT.

## What must change for Rebot

| Item | OpenESC | Rebot module | Why |
|---|---|---|---|
| MOSFET | DOY180N03T, **30 V** | **60 V** 3x3 DFN | 6S LiHV is 26.1 V before regen spikes; 30 V has no margin (OpenESC is rated to 25.2 V and dropped its TVS because the rail is so close to Vds). |
| Current | 40 A/ch continuous | 20–30 A peak phase | Drive-only; smaller copper, fewer parts. |
| Layers | 6, 2 oz | probably 4 | Lower current; cost. |
| Gate rail | onboard buck to 10 V | likely 10 V from the carrier | One buck on the carrier instead of one per module (open). |
| Bulk caps | 22 × 10 µF on board | a few, plus the carrier's bank | Modules sit millimetres from the carrier's bulk capacitance. |

## Candidate parts (JLC catalog, 2026-10-11; all Extended, none Preferred)

| Function | Part | LCSC | Stock | Unit $ | Notes |
|---|---|---|---|---|---|
| MCU | AT32F421G8U7, QFN-28 4x4 | C2765098 | 5.9k | 0.96 | Same as reference. |
| Gate driver | NSG2065Q, QFN-24 4x4 | C41414478 | 5.0k | 0.49 | Same as reference. Datasheet: floating channel to +250 V, 5–20 V supply, integrated bootstrap diode. |
| Gate driver alt. | JSM6288Q (FD6288 clone) | C19077370 | 30k | 0.50 | Common in AM32 ESCs, but its input polarity differs: needs a different AM32 target. Fallback only. |
| MOSFET | HSBB6066, PRPAK3x3-8L | C2828498 | 28.5k | 0.53 | 60 V, 5.2 mΩ @10 V, 33 nC. |
| MOSFET alt. | AON7264E, DFN-8 3x3 | C431191 | 52k | 0.27 | 60 V, 13.3 mΩ @4.5 V (Alpha & Omega). |

Datasheets were downloaded for NSG2065Q, JSM6288Q, HSBB6066 and AON7264E. The pinouts get verified
through `/add-part` when the module's circuit is written.

## Open questions

- **Header current.** Motor phases through a board-to-board header at 20–30 A peak: 2.54 mm pins are
  rated about 3 A each continuous. Options: 3 pins per phase (2×8 header, ~20×5 mm), a higher-current
  board-to-board connector, or carrying the phases through the screw/standoff joints. Needs a decision
  before the module outline.
- Gate rail from the carrier (10 V) or a buck per module (isolation vs area).
- Per-module current sense (shunt + amplifier on PA3) vs carrier-level only.
- MOSFET choice: compare the switching loss (Qg) and the dead time the AM32 target sets (60).
