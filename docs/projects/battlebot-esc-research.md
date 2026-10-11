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

## Deep dive (2026-10-11): our own part choices

**JLC tiers.** The full Basic (351) and Preferred (1235) lists were downloaded and filtered. They hold
**no** power MOSFET above 30 V / a few amps, **no** three-phase gate driver, and **no** MCU that AM32
supports (Preferred MCUs are F030/F103/L151/ATmega/STM8). So the ESC's core parts are Extended no
matter what; everything else (passives, 50 V MLCCs, LDO) can be Basic. Extended parts were then
ranked by fit, stock (popular, low supply risk) and price.

**MCU: AT32F421G8U7 stays, on merit.** Cheapest AM32-capable MCU at JLC ($0.96, Cortex-M4 120 MHz,
105 °C), the most common MCU in current AM32 ESCs, and it keeps the stock `OPENESC_20_F421` firmware.
Alternatives: GD32E230G8U6 (C380534), STM32G031G8U6 (C432211); STM32F051/G071/L431 are scarce or
expensive at JLC.

**Gate driver: TI DRV8300DRGER instead of NSG2065Q.** Genuine TI, 100 V, integrated bootstrap diodes,
adjustable dead time (DT pin), 23.7k in stock, $0.59. INHx/INLx are active-high with MODE floating,
the same polarity as the NSG2065Q ("in phase" in its datasheet), so the AT_B pin mapping and stock
firmware still apply. GVDD 5–20 V: fed with ~12 V from the carrier.
- DRV8328 was considered: it runs straight from the battery (to 60 V, VDS overcurrent protection)
  and AM32 already supports it (ARK 4IN1, F051 targets). But only the C/D variants have the 3.3 V
  LDO, and DRV8328C has 33 in stock at JLC. Kept as a watch item.

**MOSFET: HSBB6066 (60 V, 5.2 mΩ @10 V, Qg 33 nC, 28.5k stock).** ~3,600 JLC MOSFETs were swept;
40–100 V single N-channel in 3x3 packages with stock ≥ 2000 were ranked. Cheaper alternative:
Siliup SP60N05GNJ (60 V, 4.7 mΩ, $0.25). Branded alternative: AON7262E (10 mΩ). A 40 V option
(Winsok WSD4070DN33) is listed but 60 V is preferred for regen margin.

**Module supplies.** The carrier provides ~12 V (one buck shared by all ESC modules) for GVDD; the module
makes 3.3 V with an HT7533 (Basic, 30 V max) from that 12 V. No buck or inductor on the module.

**Module connection (decided 2026-10-11): one 2×9 2.54 mm header carries everything.** Screw joints
(SMD M2 standoffs carrying the phases) and pogo pins were considered and dropped: too many parts and
failure points for a v1, and 5 screws per module for a rigid two-edge clamp.
- Pins: phases A/B/C 3 each (9), battery + 3, GND 4, 12 V gate supply 1, DShot 1 = 18. About 3 A per
  pin continuous, so ~9 A per phase continuous with short 20–30 A peaks; parallel pins mean one weak
  contact doesn't cut a function. Check against the first fight logs.
- Through-hole on both sides (insertion forces and hits): female socket on the carrier, e.g.
  HC-PM254-8.5H-2x9PZ (C22373914, 8.5 mm tall, 2.5k stock, $0.19); male header on the module, e.g.
  HX PZ2.54-2x9P ZZ (C42372517, 6.2k stock, $0.14). Lower-profile sockets still to be checked.
- Retention: **one M2 screw** through the module centre into a standoff on the carrier (no current),
  preferred; the design must also work with **only Kapton tape** over the module.
- Module grows to about 25 × 15 mm. Stack ≈ 15 mm (TPU pad 1.5 + carrier 1.6 + socket 8.5 + module 1.0 +
  parts ~2), so the modules sit at the **two ends** of the channel (≈35 mm deep at the wheel end,
  17–20 mm at the centre end), not at the 13–15 mm waist. Confirm against the CAD at placement.
- If it misbehaves, redesign in v2.

**Placement.** The two modules are identical boards mounted **180° from each other**, one at each end
of the carrier, so each faces its own motor: right module at the wheel end, left module at the centre
end (where the left motor's wires arrive). AM32 reverses direction in software.

## Open questions

- Lower-profile 2×9 socket (reduces the stack).
- Header current per function: verify from the first fight logs.
- Per-module current sense (shunt + amplifier on PA3) vs carrier-level only.
- MOSFET choice: compare the switching loss (Qg) and the dead time the AM32 target sets (60).
