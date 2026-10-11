# rebot-esc — checks FAIL

136 errors · 0 warnings · 0 waived  
board 34.05 × 21.05 mm · 58 footprints · 0 track segments · 0 vias · 0 mm copper

## circuit
- ✓ `circuit/assertion` MOSFET Vds: spike budget vs 60 V rating: 40 V in [0, 48]
- ✓ `circuit/assertion` BEMF divider at full LiHV vs 3.3 V MCU: 2.373 V in [0, 3.3]
- ✓ `circuit/assertion` BEMF clamp current at spike (10k series): 0.00364 A in [0, 0.005]
- ✓ `circuit/assertion` Buck Vin: spike budget vs LMR36506 65 V: 40 V in [0, 58.5]
- ✓ `circuit/assertion` Gate rail = GVDD within DRV8300 4.8-20 V: 11 V in [4.8, 20]
- … 8 more `circuit/assertionok`

## schematic
- ✓ `schematic/pins_match` all 195 symbol pins match parts.yaml
- ✓ `schematic/netlist_match` KiCad's netlist of the schematic equals circuit.py (43 nets)

## erc
- ✓ `erc/ok` KiCad ERC: no violations

## drc
- ✗ `drc/unconnected` unconnected: PTH pad 1 [PH_A] of J2; Pad 1 [PH_A] of R11 on F.Cu
- ✗ `drc/unconnected` unconnected: PTH pad 1 [VBAT] of J1; Pad 1 [VBAT] of C17 on F.Cu
- ✗ `drc/unconnected` unconnected: PTH pad 2 [VBAT] of J1; PTH pad 1 [VBAT] of J1
- ✗ `drc/unconnected` unconnected: PTH pad 3 [VBAT] of J1; PTH pad 1 [VBAT] of J1
- ✗ `drc/unconnected` unconnected: PTH pad 4 [GND] of J1; PTH pad 6 [GND] of J1
- … 131 more `drc/unconnectederror`

## parity
- ✓ `parity/ok` board matches the schematic (KiCad schematic parity)

## placement
- ✓ `placement/near` C9 -> U1 pad 17: 1.51 mm (max 2.0) — MCU VDD decoupling
- ✓ `placement/near` C10 -> U1 pad 5: 2.85 mm (max 3.4) — VDDA decoupling
- ✓ `placement/near` C11 -> U1 pad 4: 2.76 mm (max 3.3) — NRST cap
- ✓ `placement/near` R4 -> U1 pad 25: 1.33 mm (max 1.8) — DShot series resistor at PB4
- ✓ `placement/near` C13 -> U2 pad 4: 1.51 mm (max 2.0) — GVDD HF decoupling
- … 21 more `placement/nearok`

## parts
- · `parts/tiers` 17 unique parts: basic 12, preferred 0, extended 5 (extended: C2870127 LMR36506RRPER, C167761 FNR3015S220MT, C2765098 AT32F421G8U7, C3655801 DRV8300DRGER, C2828498 HSBB6066)

## routing
- · `routing/stats` 0 bends total; per net: 
