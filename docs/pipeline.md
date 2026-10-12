# Pipeline

Every stage is text in → text/image out, runs from the command line, and has a check an
agent can run on its own. Proven end to end on `boards/pipeline-demo` (2026-10-11).

```
circuit.py ──validate/assert──▶ build/work/netlist.json            reports/circuit.json
   schematic.py (+ schematic.yaml layout) ─▶ work/<board>.kicad_sch ─▶ ERC, KiCad netlist == circuit.py,
       symbol-vs-parts.yaml pin names ─▶ reports/erc.json, schematic.json, renders/schematic.png
mechanical/outline.py ────────▶ build/work/geometry.json
placement.yaml + routing.yaml ─┐
                               ▼
   kijobs/build_board.py (KiCad pcbnew): new board, rules, net classes, outline, footprints,
   pad nets, placement, scripted tracks/vias, zones ──▶ build/work/<board>.kicad_pcb
                               ▼
   kijobs/specctra.py export ─▶ [route.lock hit? reuse route.lock.ses]
       / Freerouting × N seeded attempts ─▶ import + straighten each ─▶ keep best score ─▶ specctra.py import
   kijobs/straighten.py: cut jogs (clearance-checked)
                               ▼
   kijobs/stitch.py: GND vias on a grid + one per orphan pour island
                               ▼
   kijobs/dump.py ─▶ reports/board.json (positions, pads, nets, lengths, vias)
                               ▼
   render.py ─▶ renders/*.png (2D layer views, placement/fab view, 3D top/bottom/iso) + work/<board>.glb
   checks.py ─▶ reports/drc.json, checks.json, summary.md      report.py ─▶ review/index.html
   fab.py ─▶ fab/<board>-gerbers.zip, -bom.csv, -cpl.csv      report.py ─▶ review/gate-N.md
   diff.py ─▶ work/diff.md + side-by-side PNGs vs a git ref
```

## Make targets

| Target | Does |
|---|---|
| `make toolchain` | one-time install (uv, Python venv, Java 25, Freerouting, KiCad-Python deps) |
| `make all BOARD=x [REROUTE=1]` | build → render → check → dashboard. **The iteration command.** |
| `make build BOARD=x` | circuit → schematic → board → route → stitch → dump |
| `make sch BOARD=x` | circuit → schematic only (+ ERC, pin table, schematic.png): seconds, no board needed |
| `make sch-open BOARD=x` | open the schematic in KiCad to improve its LAYOUT; save, then `make sch` imports it |
| `make render[-fast] BOARD=x` | renders (fast = 2D only) |
| `make check BOARD=x` | all checks; exits non-zero on any unwaived error |
| `make fab BOARD=x` | JLC gerbers zip + BOM + CPL |
| `make gate BOARD=x GATE=n` | review packet for gate n |
| `make diff BOARD=x [REF=HEAD]` | semantic + visual diff vs committed results |
| `make parts BOARD=x [REFRESH=1]` | JLC tier / stock / price per part |

## Routing quality and reproducibility

Freerouting is deterministic per input file but sensitive to item order. The pipeline routes
`autoroute.attempts` times (default 5) with the DSN in canonical order plus a seeded permutation per
attempt, straightens jogs in each result, and keeps the best `routeq.score`
(20·jogs + 3·vias + 1·bends + 1·mm of copper). All attempts and scores are recorded in `route.lock.json`.

The chosen routing is locked like a dependency: `boards/<name>/route.lock.json` holds a
canonical fingerprint of the DSN input and `route.lock.ses` the routing. If the input is
unchanged, the locked routing is reused, so the same sources always give a byte-identical
`board.json`. Any change to parts/placement/nets/rules changes the fingerprint and reroutes.
Force a fresh route with `make all BOARD=x REROUTE=1`. Commit both lock files.

## Authoring conventions

- **Coordinates**: mm; board origin at top-left of the outline's bounding box; +X right,
  **+Y down**; rotation in degrees, CCW as seen from the top. Bottom-side parts: `side: bottom`.
- **circuit.py** defines `circuit() -> Circuit`. Use `c.part(ref, lib_key)` for parts in
  `lib/parts.yaml`, `c.passive(ref, "R"|"C"|"LED", value, size, lcsc=...)` for 2-pin parts,
  `c.connect(net, *pins)`, `c.nc(*pins)`, `c.net_class(NetClass(...), *nets)`, `c.check(...)`,
  `with c.block("name"):` (groups parts into a framed block in the schematic) and
  `c.power_flag(*nets)` (nets powered from off the board, e.g. USB VBUS/GND; ERC needs it).
- **schematic.yaml** (optional): schematic LAYOUT only. See "Schematic" below.
- **outline.py** defines `board()` returning shapely geometry (outline, cutouts, keepouts,
  height zones). Derive from chassis CAD when there is one, and name the feature each value comes from.
- **placement.yaml** `parts:` gives every footprint `at/rot/side`; `rules:` (near, on_edge) are
  checked. Positions are written by the agent and reviewed at gate 2.
- **routing.yaml**: `tracks`/`vias` (scripted critical copper, placed before autorouting),
  `zones`, `stitch`, `autoroute` (passes, timeout).
- **board.yaml**: layers, thickness, assembly tier, quantity, silk refs, per-board rule overrides.

## Schematic (pcbkit/schematic.py)

A review view generated from circuit.py every build, so the wiring can be checked against datasheets
before any copper exists (gate 1). One sheet, KiCad stock symbols (`symbol:` in parts.yaml; R/C/LED
automatic), a global net label on every pin and a no-connect flag on every NC pin, parts grouped by
`c.block(...)`, PWR_FLAGs for `c.power_flag(...)` nets. Symbols are copied into a project library
(`work/pcbkit.kicad_sym` + `sym-lib-table`), so the file doesn't depend on the user's KiCad setup.

**Who owns what (why human edits can't break anything):**
- Connectivity = circuit.py only. Labels, NC flags and symbol pins are regenerated every build.
- Layout = `boards/<name>/schematic.yaml`: symbol position/rotation/mirror, Reference/Value positions,
  and hand-drawn wires, labels, junctions and text notes. Parts not in it are auto-placed (new parts
  land below the existing layout). Without the file, everything is auto-placed.
- Harvest: the build records the hash of the schematic it wrote. If the file changed (someone moved
  things in KiCad and saved), the next `make sch`/`make build` copies the layout into schematic.yaml
  *before* regenerating. Moving a symbol just moves its labels with it.
- Hand-drawn wires/labels are validated: a wire group touching pins of two nets, or a label naming
  a different net than the pin it sits on, is dropped and reported as an error
  (`schematic/user_wire_short`, `user_label_wrong_net`): either the drawing or circuit.py is wrong.
  Symbols added in KiCad are ignored. To change the circuit, edit circuit.py.

**Checks it adds:** `schematic/pin_name` (KiCad symbol pin name vs parts.yaml name per pad; synonyms
like VSS/GND and VIN/VI are accepted, other spelling-only differences need `symbol_aliases:`),
`schematic/pin_unmapped`, `schematic/netlist_match` (KiCad's netlist of the drawing == circuit.py,
pad for pad), `erc/*` (KiCad ERC with pin electrical types), and `parity/*` (DRC `--schematic-parity`:
the board matches the schematic). NC pads: KiCad's `unconnected-(…)` nets == our net-less pads.
The symbol is an independent second opinion on the pinout, not proof: a library symbol can be wrong
too, and both must still be checked against the datasheet at gate 1.

## Custom checks (pcbkit/checks.py)

circuit validation + assertions · KiCad DRC (all severities, unconnected items) ·
placement rules · assembly tier (sides, min package, min board size) · JLC part lookup
(tier counts, stock vs quantity, pinout evidence present) · current capacity vs IPC-2221
per net class · routing quality (jogs, off-45° segments, bends) · missing 3D models · waivers.

**Layout hygiene (`pcbkit/layout.py`, `layout/*`)**: geometry DRC doesn't judge, run on the copper polygons that
`kijobs/copper.py` exports after stitching (`build/work/copper.json`). Configured in `routing.yaml layout:`.

| Check | What it flags | Default |
|---|---|---|
| `layout/return_path` | signal track length with no GND under it on its reference layer (nearest plane: F↔In1, In2↔B on JLC 4-layer; F↔B on 2-layer). Own vias' clearance holes don't count. | warn > 0.3 mm per net |
| `layout/finger` | dead-end GND pour tongues narrower than 0.8 mm and longer than 8 mm (~λ/20 at 1 GHz on FR4) with no via/pad (stubs that ring/radiate) | always on |
| `layout/loop` | area enclosed by a listed current loop's pads (e.g. buck VIN-cap-GND), and whether each same-net hop is joined on the parts' layer or has a GND via within 1.5 mm of each pad | per `loops:` |
| `layout/pair` | differential pair length skew, layers and via count alike | per `pairs:` |
| `layout/vias` | via count on sensitive nets (each via changes the return-current plane) | per `sensitive:` |

Floating copper is handled earlier: `routing.yaml fanout:` gives every small SMD pad of the net (GND) its own
short track + via before routing (so the router keeps them clear), pours delete unconnected islands, the stitcher
puts a via in every island that still touches a pad, and DRC fails on anything left unconnected.

## Environment notes

- WSL2 Ubuntu 22.04 drives the **Windows** KiCad 10.0.5 install via `toolchain/bin/kicad-cli`
  and `toolchain/bin/kipy` (path translation; KiCad's Python ignores PYTHONPATH, so kipy
  injects `tools/` and `toolchain/.kipy-site` itself).
- Freerouting 2.4.1 on Temurin JRE 25 in `~/.local/opt`. KiCad 10's CLI has no DSN/SES
  commands; we use pcbnew's `ExportSpecctraDSN`/`ImportSpecctraSES`.
- atopile was evaluated and dropped (decision 0002).

## Known limitations / next improvements

- Schematic: one sheet, single-unit symbols only (multi-unit, e.g. quad op-amps, not yet), simple
  row auto-layout; power nets are labels, not power symbols.
- Placement is explicit (agent-written coordinates + rules), not an optimizer.
- No mechanical interference check against chassis CAD yet (needs chassis files; planned:
  STEP export of the board vs chassis STEP, plus height zones from outline.py).
- No panelization yet (needed for Standard PCBA boards under 70×70 mm).
- Autorouter output is functional, not pretty: route anything sensitive by script.
- CPL rotation table is unverified until the first real JLC order.
