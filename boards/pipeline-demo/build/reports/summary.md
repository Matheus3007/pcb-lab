# pipeline-demo — checks PASS

0 errors · 0 warnings · 2 waived  
board 30.05 × 24.05 mm · 11 footprints · 43 track segments · 47 vias · 66.7 mm copper

## circuit
- ✓ `circuit/assertion` LED current @Vf=1.8V: 0.0015 A in [0.0005, 0.005]
- ✓ `circuit/assertion` LED current @Vf=2.4V: 0.0009 A in [0.0005, 0.005]
- ✓ `circuit/assertion` LDO input max vs XC6206 6.0V rating: 5.25 V in [0, 6]
- ✓ `circuit/assertion` LDO dissipation @100mA, Vin=5.25V: 0.195 W in [0, 0.25]

## drc
- ! `drc/silk_edge_clearance` Silkscreen clipped by board edge (board setup constraints silk clearance 0.1500 mm; actual 0.0000 mm): Polygon on Edge.Cuts; Segment of J1 on F.Silkscreen _(waived: USB-C footprint silk outline intentionally crosses the board edge (connector overhang marker); clipped by fab)_
- ! `drc/silk_edge_clearance` Silkscreen clipped by board edge (board setup constraints silk clearance 0.1500 mm; actual 0.0000 mm): Polygon on Edge.Cuts; Segment of J1 on F.Silkscreen _(waived: USB-C footprint silk outline intentionally crosses the board edge (connector overhang marker); clipped by fab)_

## placement
- ✓ `placement/near` C1 -> U1 pad 3: 1.54 mm (max 3.0) — LDO input cap
- ✓ `placement/near` C2 -> U1 pad 2: 1.47 mm (max 3.0) — LDO output cap
- ✓ `placement/on_edge` J1 courtyard -0.52 mm from top edge — USB-C mouth must reach the board edge

## parts
- · `parts/tiers` 7 unique parts: basic 6, preferred 0, extended 1 (extended: C165948 TYPE-C-31-M-12)

## current
- ✓ `current/width` VBUS: min track 0.4 mm vs 0.033 mm needed for 0.2 A (IPC-2221, ΔT 10 °C, 1.0 oz)
- ✓ `current/width` 3V3: min track 0.4 mm vs 0.033 mm needed for 0.2 A (IPC-2221, ΔT 10 °C, 1.0 oz)
