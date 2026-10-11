# rebot-ctrl — checks FAIL

142 errors · 0 warnings · 5 waived  
board 30.05 × 28.05 mm · 58 footprints · 0 track segments · 0 vias · 0 mm copper

## circuit
- ✓ `circuit/assertion` Buck Vin: spike budget vs LMR36506 65 V: 40 V in [0, 58.5]
- ✓ `circuit/assertion` Buck output (RFBT 100k / RFBB 22k): 5.545 V in [5.3, 5.8]
- ✓ `circuit/assertion` +5V rail after the OR diode (receiver supply): 5.195 V in [4.75, 5.5]
- ✓ `circuit/assertion` +5V vs XC6206 6.0 V max input: 5.545 V in [0, 6]
- ✓ `circuit/assertion` XC6206 headroom (dropout ~0.25 V @ 100 mA): 1.895 V in [0.4, 3]
- … 7 more `circuit/assertionok`

## schematic
- ✓ `schematic/pins_match` all 209 symbol pins match parts.yaml
- ✓ `schematic/netlist_match` KiCad's netlist of the schematic equals circuit.py (44 nets)

## erc
- ! `erc/pin_to_pin` Pins of type Bidirectional and Power output are connected: Symbol U4 Pin 2 [SDX, Bidirectional, Line]; Symbol #FLG02 Pin 1 [Power output, Line] _(waived: LSM6DSV32X DS13511 table 2: SDx must be tied to VDD_IO or GND when the analog hub/Qvar is unused; tied to GND)_
- ! `erc/pin_to_pin` Pins of type Bidirectional and Power output are connected: Symbol U5 Pin 3 [~{WP}/IO_{2}, Bidirectional, Line]; Symbol U3 Pin 2 [VO, Power output, Line] _(waived: W25Q128JV: /WP tied high for standard (non-quad) SPI, as the datasheet requires; IO2 is never driven)_
- ! `erc/pin_to_pin` Pins of type Bidirectional and Power output are connected: Symbol U5 Pin 7 [~{HOLD}/~{RESET}/IO_{3}, Bidirectional, Line]; Symbol U3 Pin 2 [VO, Power output, Line] _(waived: W25Q128JV: /HOLD tied high for standard (non-quad) SPI, as the datasheet requires; IO3 is never driven)_

## drc
- ✗ `drc/unconnected` unconnected: PTH pad SH [GND] of J3; PTH pad SH [GND] of J3
- ✗ `drc/unconnected` unconnected: PTH pad SH [GND] of J3; PTH pad SH [GND] of J3
- ✗ `drc/unconnected` unconnected: PTH pad SH [GND] of J3; Pad 2 [GND] of C10 on F.Cu
- ✗ `drc/unconnected` unconnected: Pad 1 [+5V] of C6 on F.Cu; Pad 1 [+5V] of D2 on F.Cu
- ✗ `drc/unconnected` unconnected: Pad 1 [+5V] of C7 on F.Cu; Pad 1 [+5V] of C6 on F.Cu
- ! `drc/silk_edge_clearance` Silkscreen clipped by board edge (board setup constraints silk clearance 0.1500 mm; actual 0.0000 mm): Polygon on Edge.Cuts; Segment of J3 on F.Silkscreen _(waived: USB-C footprint silk outline intentionally reaches the board edge (connector overhang marker, as in pipeline-demo); clipped by fab)_
- ! `drc/silk_edge_clearance` Silkscreen clipped by board edge (board setup constraints silk clearance 0.1500 mm; actual 0.1400 mm): Polygon on Edge.Cuts; Segment of J3 on F.Silkscreen _(waived: USB-C footprint silk outline intentionally reaches the board edge (connector overhang marker, as in pipeline-demo); clipped by fab)_
- … 137 more `drc/unconnectederror`

## parity
- ✓ `parity/ok` board matches the schematic (KiCad schematic parity)

## placement
- ✓ `placement/near` C10 -> U1 pad 23: 3.87 mm (max 4.4) — MCU VDD (pin 23) decoupling
- ✓ `placement/near` C11 -> U1 pad 35: 2.11 mm (max 2.6) — MCU VDD (pin 35) decoupling
- ✓ `placement/near` C12 -> U1 pad 48: 1.58 mm (max 2.1) — MCU VDD (pin 48) decoupling
- ✓ `placement/near` C15 -> U1 pad 21: 2.82 mm (max 3.3) — VDDA HF decoupling
- ✓ `placement/near` C14 -> U1 pad 21: 1.78 mm (max 2.3) — VDDA bulk
- ✓ `placement/on_edge` J1 courtyard -0.18 mm from top edge — ESC cable plugs in from the top edge
- ✓ `placement/on_edge` J3 courtyard -0.52 mm from top edge — USB-C mouth at the top edge (reachable with the lid off)
- ✓ `placement/on_edge` J2 courtyard -0.17 mm from left edge — receiver cable comes from the robot left side
- … 18 more `placement/nearok`

## parts
- · `parts/tiers` 24 unique parts: basic 15, preferred 1, extended 8 (extended: C160407 SM08B-SRSS-TB(LF)(SN), C189895 SM04B-GHS-TB(LF)(SN), C165948 TYPE-C-31-M-12, C2870127 LMR36506RRPER, C167761 FNR3015S220MT, C529356 STM32G431CBU6, C22461202 LSM6DSV32XTR, C190862 W25Q128JVPIQ)

## routing
- · `routing/stats` 0 bends total; per net: 
