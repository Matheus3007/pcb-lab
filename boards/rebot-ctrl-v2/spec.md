# rebot-ctrl-v2: spec

Status: in progress (all gates pre-approved by the owner, 2026-10-13: "go full throttle without asking") ·
Owner: Matheus3007 · Assembly tier: see board.yaml · Project context: `docs/projects/battlebot.md` (Plan).

## Purpose
Same concept and circuit as `boards/rebot-ctrl` (v1): mini controller for Rebot (3 lb undercutter) between the
ELRS receiver and an off-the-shelf 4-in-1 ESC (HAKRC 32BIT 40A candidate, or the Flywoo GOKU G45M): CRSF in,
bidirectional DShot out (left drive / right drive / weapon / spare), gyro turn-rate control, fight logging, USB
for logs/config/firmware. Powers the receiver from its own 65 V-rated buck.

**v2 goal (owner, 2026-10-13): smaller than v1 (30 × 28 mm), using the 4 layers so the traces still route cleanly.**

## Mechanical
- Taped onto the 4-in-1 (HAKRC 31 × 30 mm / G45M 33 × 30 mm): must fit inside it. Stack stands in the rear
  channel (≈31 mm free height). Outline: see `mechanical/outline.py` (25 × 25 mm, 26 % less area than v1's 30 × 28).
- Parts on the top side only. SWD/boot test pads on the bottom side (unassembled copper pads).
- Connectors on the same edges as v1, mouths out: ESC JST-SH 8P and USB-C on the top edge (**order swapped vs v1:
  ESC connector top-left, USB-C top-right**, so the MCU sits right under the ESC pins), receiver JST-GH 4P on the
  left edge (lower half).
- Mass target ≤ v1. No mounting holes (taped). Shock first: small packages, locking connectors.

## Electrical
- Layers: 4 · copper 1 oz · thickness 1.0 mm · vias 0.3 mm drill / 0.45 mm pad (JLC's no-surcharge via option).
- **Stackup: F.Cu signal | In1.Cu solid GND | In2.Cu signal | B.Cu solid GND.** JLC's thin prepreg sits between
  F/In1 and In2/B, so each signal layer has a solid GND plane right next to it (layout/return_path), In2's
  traces are shielded on both sides, and the bottom face toward the ESC's switching FETs is solid copper.
- Input, rails, connector pinouts: identical to v1 (`boards/rebot-ctrl/spec.md`): J1 ESC JST-SH 8P
  1 GND, 2 VBAT, 3 M1, 4 M2, 5 M3, 6 M4, 7 CURR, 8 TLM; J2 receiver JST-GH 4P 1 +5V, 2 GND, 3 receiver TX,
  4 receiver RX; J3 USB-C (HRO TYPE-C-31-M-12).
- MCU **STM32G431KBU6** (UFQFPN-32, 5 × 5 mm) instead of v1's CBU6 (7 × 7 mm). Pin map (firmware):

  | Function | Pin | Peripheral |
  |---|---|---|
  | DShot M1-M4 | PA0, PA1, PA2, PA3 | TIM2_CH1-CH4 (AF1), bidirectional (input capture) |
  | ESC current (/11) | PA4 | ADC2_IN17 |
  | VBAT sense (/11) | PF0 | ADC1_IN10 |
  | ESC telemetry RX | PA15 | USART2_RX (AF7) |
  | CRSF RX / TX | PA9 / PA10 | USART1 (AF7) **with TX/RX swap (USART_CR2.SWAP = 1)** |
  | USB DM / DP | PA11 / PA12 | USB FS (HSI48 + CRS) |
  | SPI SCK / MISO / MOSI | PB3 / PB4 / PB5 | SPI1 (AF5) |
  | IMU CS / INT1 | PB6 / PA8 | GPIO / EXTI8; IMU shares SPI1 with the flash: set IF_CFG.I2C_I3C_disable at init |
  | Flash CS | PB7 | GPIO (GD25Q128E: JEDEC ID C8 40 18; accept Winbond EF 40 18 too) |
  | Status LED | PB0 | GPIO (active high) |
  | NRST / BOOT0 | PG10 / PB8 | 10k pull-down on BOOT0 |
  | SWDIO / SWCLK | PA13 / PA14 | bottom test pads |
  | spare (NC) | PA5, PA6, PA7, PF1 | |

## Parts policy
- As v1. Both ORing diodes are B5819WS (SOD-323, JLC Preferred): one unique part fewer than v1.
- Log flash GD25Q128EWIGY (pin-compatible with the W25Q128JVPIQ, cheaper). ADC filter caps share the 100 nF line
  (CURR bandwidth ~175 Hz: enough for logging). Fallback MCU if stock runs out: STM32G431KBU3.

## Fab
- Quantity 5 · **lead-free HASL · green mask · Standard assembly**, one side, edge rails added by JLC (owner, 2026-10-25:
  cost cut from $256 to ~$188 for 5). Standard is forced anyway: the LSM6DSV32X is a JLC "Standard Only" part.

## Open questions
- (none: gates pre-approved)

## Changelog
| Date | Change / gate | Notes |
|---|---|---|
| 2026-10-13 | Scaffolded from v1 | Owner asked for a smaller v2 using the 4 layers; gates pre-approved |
| 2026-10-13 | gate 1 (pre-approved) | 13 assertions pass, ERC 3 datasheet tie-offs waived (as v1), 191 pins match; STM32G431KBU6 added to lib/parts.yaml from DS12589 |
| 2026-10-13 | gate 2 (pre-approved) | 25 × 25 mm: ESC JST-SH top-left over the MCU (DShot fan straight down), USB-C top-right, receiver JST-GH bottom-left; IMU beside the MCU's SPI side, flash beyond, buck/LDO bottom right; test pads on the bottom |
| 2026-10-13 | gate 3 (pre-approved) | checks PASS (0 errors, 0 warnings, 41 waived with reasons); signals on F + In2, In1/B solid GND; USB pair scripted on In2 round the right edge; fab files generated, not ordered |
| 2026-10-25 | JLC cost cut (owner) | vias 0.2/0.45 -> 0.3/0.45 (no via surcharge, Kelvin test, TG155), HASL + green, Standard PCBA (IMU is Standard-only), flash -> GD25Q128EWIGY, C17/C18 10 nF -> 100 nF (one BOM line fewer); CPL: U1 -90, J2 0 (JLC preview) |
