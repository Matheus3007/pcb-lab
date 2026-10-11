---
name: board-iteration
description: The pcb-lab design loop. Edit circuit/outline/placement/routing, run make all, read the check summary, look at the renders, fix DRC and custom-check failures using the playbook, and commit with a semantic diff. Use for any change to an existing board in boards/.
---

# Iterate on a board

## The loop
```bash
make all BOARD=<name>            # build → render → check → dashboard (~45 s small board)
```
1. Read `boards/<name>/build/reports/summary.md` (printed by make). Fix errors from the top of each group.
2. **Look at the renders** with Read: always `placement.png` and `3d_iso.png`, plus `top.png`,
   `copper_top.png` and `copper_bottom.png` once routed. Describe what you see; look for parts too close to edges,
   connectors not facing out, ugly routing, silk on pads, 3D models misaligned or missing.
3. Repeat until `checks PASS` and the renders look right.
4. `make diff BOARD=<name>` → put the highlights in the commit message. Commit sources +
   `build/reports` + `build/renders` + `build/review` + `route.lock.*`.

Faster partial runs: `make build`, `make render-fast` (2D only), `make check`.

## Routing determinism
Routing comes from `route.lock.ses` while the routing input is unchanged. Any placement, net, rule or
outline change reroutes everything (unrelated nets can move). `REROUTE=1` forces a fresh route,
e.g. to try for a better result. Freerouting is random, so several attempts may give different quality.

## Playbook: failure → fix
| Finding | Usual cause | Fix |
|---|---|---|
| `circuit/unconnected_pin` | pad not on a net and not `c.nc()` | connect it or mark NC deliberately |
| `circuit/single_pin_net` | typo in net name, or a net with one pin | fix name, or connect the other end |
| `circuit/assertion` | design intent violated | change values/parts, never loosen the bound silently |
| `drc/shorting_items`, `courtyards_overlap`, `pth_inside_courtyard` | placement overlap | move parts (placement.png shows courtyards in magenta) |
| `drc/unconnected` zone↔zone | pour island not tied to the other layer | stitching (`routing.yaml stitch:`) adds island vias; if "no room", move parts or widen the gap |
| `drc/unconnected` pad↔pad | autorouter failed | check `build/work/freerouting.log`; increase spacing, add a scripted track, or `REROUTE=1` |
| `drc/starved_thermal` | thermal spokes blocked | zones use THT-only thermals; for THT pads clear space around them |
| `drc/silk_*` | refs/values over pads or edges | `silk_refs: false` on dense boards; waive edge-connector silk with a reason |
| `drc/clearance`, `track_width` | rules vs net classes | check `toolchain/rules/jlc.yaml` and NetClass widths in circuit.py |
| `placement/near` | decoupling/feedback part too far | move it next to the named pad (`make footprint` gives pad positions) |
| `placement/on_edge` | connector not at the edge | position = edge − (origin→mouth distance), see the footprint's fab extent |
| `assembly/side` / `package` | violates assembly tier | move to the top side / bigger package, or change tier with the human |
| `parts/stock` | low stock at JLC | pick an alternative, re-verify pinout |
| `current/width` | trace too thin for the class current | raise NetClass `track_width` or use a pour |
| `models/missing` | no 3D model | `/add-part` step 4 |
| `routing/jog` | autorouter sideways step the straightener couldn't fix (no clearance) | `REROUTE=1` (more `attempts`), nudge the parts causing the squeeze, or script that net in `routing.yaml` |
| `schematic/pin_name` | KiCad symbol and parts.yaml disagree on a pad's function | read the datasheet: fix `pins` (wrong pinout!) or add `symbol_aliases` (spelling only) |
| `schematic/pin_unmapped` | symbol pin numbers ≠ footprint pads | pick a symbol matching the footprint, or a local symbol in lib/symbols/ |
| `schematic/user_wire_short`, `user_label_wrong_net` | a hand-drawn wire/label contradicts circuit.py | the human may have found a real bug: ask; else remove it from schematic.yaml |
| `erc/power_pin_not_driven` | power-input pin with no source on its net | regulator output missing, or an off-board supply: `c.power_flag("NET")` |
| `erc/*` other | pin-type conflicts (two outputs together, input undriven) | fix circuit.py; KiCad's ERC knows pin types we don't |
| `parity/*` | board and schematic disagree | pipeline bug (both come from netlist.json): fix the generator, never waive |
| `parts/extended` | plain Extended part without justification | find a Basic/Preferred alternative (`/add-part`), or add `extended_reason:` |

## Routing quality (no unneeded bends)
- Read `routing/stats` (bends per net) and look at `copper_top.png`/`copper_bottom.png` for detours,
  loops around parts, and staircase paths. A net with many more bends than its neighbours is suspect.
- `route.lock.json` lists every attempt's score (jogs, vias, bends, length). Raise `autoroute.attempts`
  for important boards; attempts are reproducible (seeded DSN ordering).
- Placement drives routing: line parts up so connected pads face each other, and the router has less to bend.
- Sensitive or high-current nets: script them (`tracks:` in routing.yaml) with straight segments and
  45° corners, before the autorouter runs.

## Placement technique
- Read pad positions first (`make footprint`, or `build/reports/board.json` after a build). Place relative to
  the pads that matter (decoupling caps at the supply pin, not the part centre).
- SOT-23-3: pin 3 is alone on the right at rot 0. Connectors: check which way the mouth faces.
- Express intent as `rules:` in placement.yaml so it stays checked after later moves.
- Keep ≥0.5 mm between courtyards and the board edge unless a part must overhang (connectors).

## Never
- Hand-edit anything in `build/`. Waive an error without a reason. Commit with `checks FAIL`
  unless the commit message says why (work in progress).
