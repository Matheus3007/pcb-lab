# rebot-esc: review gate 2
_generated 2026-10-11 17:35 · checks FAIL_

## Renders
![placement](../renders/placement.png)
![3d iso](../renders/3d_iso.png)
![3d top](../renders/3d_top.png)
![3d bottom](../renders/3d_bottom.png)

## Placement rules
- ✓ C9 -> U1 pad 17: 1.51 mm (max 2.0) — MCU VDD decoupling
- ✓ C10 -> U1 pad 5: 2.85 mm (max 3.4) — VDDA decoupling
- ✓ C11 -> U1 pad 4: 2.76 mm (max 3.3) — NRST cap
- ✓ R4 -> U1 pad 25: 1.33 mm (max 1.8) — DShot series resistor at PB4
- ✓ C13 -> U2 pad 4: 1.51 mm (max 2.0) — GVDD HF decoupling
- ✓ C12 -> U2 pad 4: 3.92 mm (max 4.4) — GVDD bulk
- ✓ C14 -> U2 pad 20: 2.59 mm (max 3.1) — bootstrap A at BSTA
- ✓ C15 -> U2 pad 17: 1.21 mm (max 1.7) — bootstrap B at BSTB
- ✓ C16 -> U2 pad 14: 1.76 mm (max 2.3) — bootstrap C at BSTC
- ✓ C18 -> U4 pad 4: 1.24 mm (max 1.7) — buck input HF cap at VIN
- ✓ C17 -> U4 pad 4: 2.25 mm (max 2.8) — buck input cap
- ✓ C19 -> U4 pad 6: 1.30 mm (max 1.8) — buck bootstrap at BOOT
- ✓ C20 -> U4 pad 7: 1.65 mm (max 2.2) — buck VCC cap
- ✓ R21 -> U4 pad 8: 1.39 mm (max 1.9) — feedback divider at FB
- ✓ L1 -> U4 pad 5: 3.08 mm (max 3.6) — inductor at SW
- ✓ C7 -> U3 pad 2: 1.97 mm (max 3.0) — LDO input cap
- ✓ C8 -> U3 pad 3: 1.74 mm (max 3.0) — LDO output cap
- ✓ R5 -> Q1 pad 4: 1.67 mm (max 2.2) — HS gate resistor A
- ✓ R6 -> Q2 pad 4: 1.67 mm (max 2.2) — LS gate resistor A
- ✓ R7 -> Q3 pad 4: 1.67 mm (max 2.2) — HS gate resistor B
- ✓ R8 -> Q4 pad 4: 1.67 mm (max 2.2) — LS gate resistor B
- ✓ R9 -> Q5 pad 4: 1.67 mm (max 2.2) — HS gate resistor C
- ✓ R10 -> Q6 pad 4: 1.67 mm (max 2.2) — LS gate resistor C
- ✓ C1 -> Q1 pad 5: 2.86 mm (max 3.4) — VBAT bulk at HS drain A
- ✓ C2 -> Q3 pad 5: 2.86 mm (max 3.4) — VBAT bulk at HS drain B
- ✓ C3 -> Q5 pad 5: 2.86 mm (max 3.4) — VBAT bulk at HS drain C

## Placement intent (from placement.yaml)
- J1: {'at': [7.0, 16.0], 'rot': 270, 'side': 'bottom'}
- H1: {'at': [2.4, 2.4]}
- Q1: {'at': [19.4, 4.4], 'rot': 0}
- Q2: {'at': [19.4, 9.8], 'rot': 0}
- Q3: {'at': [24.6, 4.4], 'rot': 0}
- Q4: {'at': [24.6, 9.8], 'rot': 0}
- Q5: {'at': [29.8, 4.4], 'rot': 0}
- Q6: {'at': [29.8, 9.8], 'rot': 0}
- R5: {'at': [22.0, 6.0], 'rot': 90}
- R6: {'at': [22.0, 11.4], 'rot': 90}
- R7: {'at': [27.2, 6.0], 'rot': 90}
- R8: {'at': [27.2, 11.4], 'rot': 90}
- R9: {'at': [32.4, 6.0], 'rot': 90}
- R10: {'at': [32.4, 11.4], 'rot': 90}
- C1: {'at': [19.4, 1.2], 'rot': 0}
- C2: {'at': [24.6, 1.2], 'rot': 0}
- C3: {'at': [29.8, 1.2], 'rot': 0}
- C4: {'at': [22.0, 1.2], 'rot': 90}
- C5: {'at': [27.2, 1.2], 'rot': 90}
- C6: {'at': [32.4, 1.4], 'rot': 90}
- R11: {'at': [17.6, 13.6], 'rot': 90}
- R12: {'at': [18.7, 13.6], 'rot': 90}
- R13: {'at': [19.8, 13.6], 'rot': 90}
- R14: {'at': [22.8, 13.6], 'rot': 90}
- R15: {'at': [23.9, 13.6], 'rot': 90}
- R16: {'at': [25.0, 13.6], 'rot': 90}
- R17: {'at': [28.0, 13.6], 'rot': 90}
- R18: {'at': [29.1, 13.6], 'rot': 90}
- R19: {'at': [30.2, 13.6], 'rot': 90}
- U2: {'at': [13.2, 8.9], 'rot': 0}
- C13: {'at': [10.05, 10.6], 'rot': 90}
- C12: {'at': [11.0, 13.0], 'rot': 0}
- C14: {'at': [16.4, 5.6], 'rot': 90}
- C15: {'at': [16.4, 8.6], 'rot': 90}
- C16: {'at': [16.4, 11.4], 'rot': 90}
- U1: {'at': [5.6, 9.0], 'rot': 0}
- C9: {'at': [8.95, 10.4], 'rot': 90}
- R3: {'at': [2.05, 6.6], 'rot': 90}
- R2: {'at': [2.05, 8.6], 'rot': 90}
- C11: {'at': [0.9, 8.6], 'rot': 90}
- R1: {'at': [2.05, 10.6], 'rot': 90}
- C10: {'at': [0.9, 10.6], 'rot': 90}
- R4: {'at': [4.9, 5.75], 'rot': 0}
- U4: {'at': [7.2, 2.6], 'rot': 0}
- C20: {'at': [7.2, 0.75], 'rot': 0}
- R21: {'at': [9.4, 1.3], 'rot': 90}
- C19: {'at': [9.4, 3.3], 'rot': 90}
- L1: {'at': [12.0, 2.3], 'rot': 0}
- C21: {'at': [15.0, 2.3], 'rot': 90}
- R20: {'at': [12.0, 4.7], 'rot': 0}
- C18: {'at': [6.0, 4.75], 'rot': 0}
- C17: {'at': [8.7, 5.3], 'rot': 0}
- U3: {'at': [3.0, 17.4], 'rot': 270}
- C7: {'at': [3.4, 13.6], 'rot': 0}
- C8: {'at': [1.0, 13.3], 'rot': 90}
