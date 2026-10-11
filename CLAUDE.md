# pcb-lab — PCBs designed entirely as code

This repo designs PCBs from zero, as text, so every change can be diffed, checked by
machine, and reviewed visually. The end product of each board is an order for a
**fully assembled board from JLCPCB** (PCB + PCBA).

The human owner reviews **results** (renders, check reports, BOM, 3D fit), not code, and
never opens the KiCad GUI. Your job is to make those results trustworthy and easy to review.

## Read first (in order)

1. `docs/pipeline.md`: stages, files, tools, the authoring conventions.
2. `docs/jlcpcb.md`: fab/assembly limits. Every design rule traces back to this file.
3. `docs/review-gates.md`: where the human signs off. Never skip a gate.
4. The board's `spec.md` (`boards/<name>/spec.md`).
5. `docs/decisions/`: why the toolchain is what it is. Don't reopen these without a new reason.
6. `docs/projects/`: context for larger projects (e.g. the battlebot).
7. `boards/pipeline-demo/`: the reference example of a complete, passing board.

## Toolchain (see docs/decisions/0001 + 0002)

| Concern | How | Source of truth |
|---|---|---|
| Circuit, parts, values, assertions | **plain Python** (`pcbkit.circuit`) | `boards/<name>/circuit.py`, `lib/parts.yaml` |
| Outline, cutouts, keepouts | **Python + shapely** | `boards/<name>/mechanical/outline.py` (+ chassis CAD) |
| Placement | explicit positions + verified rules | `boards/<name>/placement.yaml` |
| Routing | scripted tracks/zones + **Freerouting** + auto GND stitching | `boards/<name>/routing.yaml` |
| Board generation | KiCad 10 `pcbnew` (Windows KiCad, driven from WSL) | regenerated every build |
| Checks | KiCad DRC (JSON) + `pcbkit.checks` | `build/reports/` |
| Renders / fab | `kicad-cli` | `build/renders/`, `build/fab/` |

**Never hand-edit a generated file** (`build/**`). Change the source and rebuild.

## Setup (once per machine)

`make toolchain` (= `toolchain/setup.sh`; no sudo; needs KiCad 10 on Windows). Then every
command goes through `make`, which sources `toolchain/env.sh` itself.

## The loop

```
edit source → make all BOARD=<name> → read build/reports/summary.md + LOOK at build/renders/*.png → fix → repeat
```

- `make all` = build → render → check (+ dashboard). ~45 s on the demo board.
- **Done for any iteration** = `make check` exits 0 **and** you have opened the renders
  (at least `placement.png`, `top.png`, `3d_iso.png`) and said what you saw. DRC can't see
  ugly or wrong-looking placement; you can.
- Warnings are fixed or waived in `boards/<name>/waivers.yaml` with a reason. No silent ignores.
- Before committing a changed board, run `make diff BOARD=<name>` and put the highlights in
  the commit message.

## Rules that are easy to get wrong

- **Pinouts and footprints pass every check even when they're wrong.** Every IC/connector entry in
  `lib/parts.yaml` needs `pinout_source` (datasheet + page/table) and `pinout_verified`.
  Get the datasheet from JLC's file endpoint (`dataManualFileAccessId`, see `pcbkit/jlc.py`),
  read the pin table, and record it. Watch for clones with different pinouts (see XC6206 note).
- **Footprint origin/orientation**: before placing a new footprint, read its pads/fab
  geometry (which way does a connector's mouth face at rot 0?) and confirm in the render.
- **Prefer JLC Basic / Preferred parts.** `make parts BOARD=x` shows the tier, stock and price.
- **3D models**: if KiCad has no model, fetch one (easyeda2kicad), re-origin it via
  `model.offset` in parts.yaml, and confirm alignment in `3d_iso.png`. Missing models make
  the mechanical-fit checks blind.
- **Assembly tier** (board.yaml `assembly_tier`) drives side/package/size checks.
- **Coordinates**: mm, board origin top-left, **+Y down** (KiCad convention), rotations CCW.
- **CPL rotations** come from `lib/jlc_rotations.csv` (community hints, unverified). The human
  confirms in JLC's preview at gate 3; confirmed corrections go at the top of that file.

## Git conventions

- One logical change per commit; message says what changed on the board and why
  (e.g. `bot-main: move IMU to board centroid to reduce vibration coupling`).
- Committed: sources, `build/reports/`, `build/renders/`, `build/review/`. Ignored:
  `build/work/` (intermediates, .kicad_pcb, .glb) and `build/fab/` (regenerated).
- Every JLC order gets a tag `<board>/vX.Y`, and its fab outputs are attached to the tag (or saved).

## Repo layout

```
Makefile                  make <target> BOARD=<name>   (make help)
toolchain/                setup.sh, env.sh, wrappers (kicad-cli, kipy, freerouting), rules/jlc.yaml
tools/pcbkit/             pipeline code: circuit, pipeline, checks, render, fab, report, diff, jlc
tools/pcbkit/kijobs/      scripts that run inside KiCad's Python (board build, DSN/SES, stitch, dump)
lib/parts.yaml            shared part definitions with pinout evidence
lib/3d/, lib/footprints/  models/footprints KiCad doesn't ship
lib/jlc_cache.json        JLC catalog cache   lib/jlc_rotations.csv  CPL corrections
boards/_template/         copy to start a board
boards/<name>/            spec.md, board.yaml, circuit.py, mechanical/, placement.yaml, routing.yaml, waivers.yaml
  build/reports|renders|review   committed results   build/work|fab   generated, ignored
docs/                     pipeline, jlcpcb, review gates, monitoring, decisions, projects
```

## Starting a new board

1. `cp -r boards/_template boards/<name>`, then fill `spec.md` **with the human**.
2. Write `circuit.py` (+ new parts in `lib/parts.yaml` with pinout evidence) → `make build` until
   the circuit validates → `make gate GATE=1` and **stop for review**.
3. Outline + placement → `make all` until clean → `make gate GATE=2` and **stop**.
4. Routing → `make all` until clean → `make fab` → `make gate GATE=3` and **stop**.
