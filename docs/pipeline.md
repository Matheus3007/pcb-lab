# Pipeline

Every stage is text in → text/image out, runs from the command line, and has a check an
agent can run on its own. Proven end to end on `boards/pipeline-demo` (2026-10-11).

```
circuit.py ──validate/assert──▶ build/work/netlist.json            reports/circuit.json
mechanical/outline.py ────────▶ build/work/geometry.json
placement.yaml + routing.yaml ─┐
                               ▼
   kijobs/build_board.py (KiCad pcbnew): new board, rules, net classes, outline, footprints,
   pad nets, placement, scripted tracks/vias, zones ──▶ build/work/<board>.kicad_pcb
                               ▼
   kijobs/specctra.py export ─▶ [route.lock hit? reuse route.lock.ses] / Freerouting ─▶ specctra.py import
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
| `make build BOARD=x` | circuit → board → route → stitch → dump |
| `make render[-fast] BOARD=x` | renders (fast = 2D only) |
| `make check BOARD=x` | all checks; exits non-zero on any unwaived error |
| `make fab BOARD=x` | JLC gerbers zip + BOM + CPL |
| `make gate BOARD=x GATE=n` | review packet for gate n |
| `make diff BOARD=x [REF=HEAD]` | semantic + visual diff vs committed results |
| `make parts BOARD=x [REFRESH=1]` | JLC tier / stock / price per part |

## Reproducibility: the route lock

Freerouting has unseeded randomness, so two runs on the same input give different routing.
Its result is therefore locked like a dependency: `boards/<name>/route.lock.json` holds a
canonical fingerprint of the DSN input and `route.lock.ses` the routing. If the input is
unchanged, the locked routing is reused, so the same sources always give a byte-identical
`board.json`. Any change to parts/placement/nets/rules changes the fingerprint and reroutes.
Force a fresh route with `make all BOARD=x REROUTE=1`. Commit both lock files.

## Authoring conventions

- **Coordinates**: mm; board origin at top-left of the outline's bounding box; +X right,
  **+Y down**; rotation in degrees, CCW as seen from the top. Bottom-side parts: `side: bottom`.
- **circuit.py** defines `circuit() -> Circuit`. Use `c.part(ref, lib_key)` for parts in
  `lib/parts.yaml`, `c.passive(ref, "R"|"C"|"LED", value, size, lcsc=...)` for 2-pin parts,
  `c.connect(net, *pins)`, `c.nc(*pins)`, `c.net_class(NetClass(...), *nets)`, `c.check(...)`.
- **outline.py** defines `board()` returning shapely geometry (outline, cutouts, keepouts,
  height zones). Derive from chassis CAD when there is one, and name the feature each value comes from.
- **placement.yaml** `parts:` gives every footprint `at/rot/side`; `rules:` (near, on_edge) are
  checked. Positions are written by the agent and reviewed at gate 2.
- **routing.yaml**: `tracks`/`vias` (scripted critical copper, placed before autorouting),
  `zones`, `stitch`, `autoroute` (passes, timeout).
- **board.yaml**: layers, thickness, assembly tier, quantity, silk refs, per-board rule overrides.

## Custom checks (pcbkit/checks.py)

circuit validation + assertions · KiCad DRC (all severities, unconnected items) ·
placement rules · assembly tier (sides, min package, min board size) · JLC part lookup
(tier counts, stock vs quantity, pinout evidence present) · current capacity vs IPC-2221
per net class · missing 3D models · waivers.

## Environment notes

- WSL2 Ubuntu 22.04 drives the **Windows** KiCad 10.0.5 install via `toolchain/bin/kicad-cli`
  and `toolchain/bin/kipy` (path translation; KiCad's Python ignores PYTHONPATH, so kipy
  injects `tools/` and `toolchain/.kipy-site` itself).
- Freerouting 2.4.1 on Temurin JRE 25 in `~/.local/opt`. KiCad 10's CLI has no DSN/SES
  commands; we use pcbnew's `ExportSpecctraDSN`/`ImportSpecctraSES`.
- atopile was evaluated and dropped (decision 0002).

## Known limitations / next improvements

- Placement is explicit (agent-written coordinates + rules), not an optimizer.
- No mechanical interference check against chassis CAD yet (needs chassis files; planned:
  STEP export of the board vs chassis STEP, plus height zones from outline.py).
- No panelization yet (needed for Standard PCBA boards under 70×70 mm).
- Autorouter output is functional, not pretty: route anything sensitive by script.
- CPL rotation table is unverified until the first real JLC order.
