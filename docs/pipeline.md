# Pipeline

Every stage is text in → text/image out, runnable from the command line, and each one has a check
an agent can run alone.

```
spec.md
  │
  ▼
[1 circuit]   .ato ──ato build──▶ layout/<build>.kicad_pcb (footprints + nets, parts picked)
  │
  ▼
[2 outline]   mechanical/outline.py (+ chassis CAD) ──▶ Edge.Cuts, cutouts, keepouts, holes
  │
  ▼
[3 place]     placement.yaml ──tools/place.py──▶ footprint positions/rotations/sides
  │                                   ── REVIEW GATE 2 (placement) ──
  ▼
[4 route]     routing.yaml ──tools/route.py──▶ critical nets + zones
              remaining nets ──DSN──▶ Freerouting ──SES──▶ import
  │
  ▼
[5 check]     kicad-cli pcb drc --format json --exit-code-violations
              + atopile assertions + tools/checks/* + mechanical interference
  │
  ▼
[6 render]    kicad-cli pcb export svg (per layer) / pcb render (3D PNG, top+bottom)
  │
  ▼
[7 fab]       gerbers + drill + pos ──▶ JLC CPL (rotation-corrected) + JLC BOM
                                     ── REVIEW GATE 3 (pre-order) ──
```

## Make targets (contract)

| Target | Does | Status |
|---|---|---|
| `make toolchain` | build/pull the pinned tool container | planned |
| `make build BOARD=x` | stages 1–4 | planned |
| `make check BOARD=x` | stage 5, writes `build/reports/*.json` + `summary.md`, exits non-zero on failure | planned |
| `make render BOARD=x` | stage 6 → `build/renders/` | planned |
| `make diff BOARD=x REF=<git ref>` | semantic diff (parts moved/added, nets changed, trace length, via count) + side-by-side renders vs REF | planned |
| `make fab BOARD=x` | stage 7 → `build/fab/` (gerbers zip, BOM.csv, CPL.csv) | planned |
| `make all BOARD=x` | build → check → render | planned |

## Stage notes

### 1. Circuit (atopile)
- One atopile project per board (`boards/<name>/ato.yaml`). Pin the atopile version in
  `toolchain/versions.env` and in `requires-atopile`.
- Use assertions for design intent (`assert v_out within 3.3V +/- 3%`), because they turn
  electrical mistakes into build errors.
- atopile writes no schematic, so KiCad ERC and schematic-parity DRC don't apply. Electrical
  checking = atopile's checks/assertions + our custom net checks.
- Parts picked from the JLC/LCSC catalog via atopile's hosted API
  (`components.atopileapi.com`), then vendored into `parts/`. Telemetry is disabled in the container.

### 2. Outline (Python)
- atopile has no language for board shape. We generate Edge.Cuts ourselves from
  `mechanical/outline.py` (shapely/build123d geometry), optionally derived from chassis
  STEP/SVG/DXF in `mechanical/chassis/`.
- Also emits: mounting holes, keepout areas (rule areas), and component height limits
  per region (used by the 3D fit check).

### 3. Placement (Python, rules-based)
- `placement.yaml` expresses intent: fixed anchors (connectors, holes, IMU), groups
  ("decoupling caps of U1 within 2 mm of their pin"), sides, height classes.
- `tools/place.py` writes positions into the `.kicad_pcb` by editing the S-expression file
  directly (or via KiCad's bundled `pcbnew` Python). The KiCad IPC API needs a running GUI, so
  we don't use it.
- Re-running atopile must not destroy placement. place.py is idempotent and is the
  only thing that sets positions.

### 4. Routing
- Critical nets (power, motor/high-current, USB pairs, IMU SPI, current-sense Kelvin
  connections) are routed **by script** from `routing.yaml`.
- The rest: DSN export via KiCad's bundled Python → Freerouting headless (Java 25) → SES import.
  `kicad-cli` has no DSN/SES commands.
- Autorouter output is the weakest part of the pipeline: always inspect renders after it.

### 5. Checks
- DRC rules come from `toolchain/jlc-<tier>.kicad_dru`, generated from `docs/jlcpcb.md`.
- Custom checks (planned, in `tools/checks/`): decoupling distance, trace width vs net
  current, Basic/Extended count, parts-near-edge, height-vs-chassis, CPL rotation sanity.
- Output: machine-readable JSON + a short `summary.md` an agent reads first.

### 6. Renders
- Per-layer SVG→PNG (F.Cu, B.Cu, silks, Edge.Cuts) + 3D top/bottom PNG.
- The agent **must** look at these each iteration (Claude can read images).

### 7. Fab outputs
- Gerbers + Excellon drill + positions via kicad-cli; BOM and CPL reformatted to
  JLC's column format. CPL rotations are corrected per package (classic JLC error) and
  verified in JLC's online preview at gate 3.

## Environment

- Dev machine: Windows + WSL2 (Ubuntu 22.04). KiCad 10.0 installed on the Windows side
  (`kicad-cli.exe` usable from WSL). WSL itself has no kicad-cli, Java, or Python 3.14.
- Plan: everything runs in a pinned container (`toolchain/`). Fallback: Windows `kicad-cli.exe` + `uv`
  managed Python 3.14 in WSL. Settle this in Phase 0.

## Phase 0: prove the pipeline (do this first)

Build `boards/pipeline-demo`: a small 2-layer board (USB-C power input → 3.3 V LDO → status LED + a
4-pin header), a non-rectangular outline with one internal cutout, Economic PCBA.
Done when every target above is implemented, `make all` and `make fab` work from a clean
checkout, and the human has passed all 3 review gates on it (no order needed).
Phase 0 must also confirm in practice: atopile vendoring into `parts/`, atopile rebuild
leaves placement alone, Freerouting round-trip, CPL rotations.
