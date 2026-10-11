# pcb-lab — PCBs designed entirely as code

This repo designs PCBs from zero, as text, so every change can be diffed, checked by
machine, and reviewed visually. The end product of each board is an order for a
**fully assembled board from JLCPCB** (PCB + PCBA).

The human owner reviews **results** (renders, check reports, BOM, 3D fit), not code.
Your job is to make those results trustworthy and easy to review.

## Read first (in order)

1. `docs/pipeline.md`: the stages, what each one reads and writes, the tools, and what's implemented so far.
2. `docs/jlcpcb.md`: fab and assembly limits. Every design rule traces back to this file.
3. `docs/review-gates.md`: where the human signs off. Never skip a gate.
4. The `spec.md` of the board you are working on (`boards/<name>/spec.md`).
5. `docs/decisions/`: why the toolchain is what it is. Don't reopen these without a new reason.
6. `docs/projects/`: context for the larger projects boards belong to (e.g. the battlebot).

## Toolchain (decided, see docs/decisions/0001-toolchain.md)

| Concern | Tool | Source of truth |
|---|---|---|
| Circuit, parts, values | **atopile** (`.ato`) | `boards/<name>/*.ato`, `parts/` |
| Board outline, cutouts, keepouts, holes | **Python** (`mechanical/outline.py`) | derived from chassis CAD in `mechanical/chassis/` |
| Placement | **Python + rules file** (`placement.yaml`) | rules, not hand-placed coordinates where avoidable |
| Routing | scripted critical nets (`routing.yaml`) + **Freerouting** for the rest | |
| Checks | **kicad-cli** DRC (JSON) + atopile assertions + `tools/` custom checks | |
| Outputs | **kicad-cli** (Gerbers, drill, pos, STEP, renders) + JLC BOM/CPL | |

KiCad 10 is the engine, but nobody opens the GUI. Generated `.kicad_pcb` files are build
outputs of the code above. **Never hand-edit a generated file.** Change the source and rebuild.

## The loop

```
edit source → make build BOARD=<name> → make check BOARD=<name> → read reports + renders → fix → repeat
```

- One command per iteration. If you find yourself running a multi-step sequence by
  hand, add it to the Makefile/tools instead.
- **Done for any iteration** = `make check` exits 0 (zero DRC errors, zero failed
  assertions, zero failed custom checks) **and** you have looked at the renders in
  `boards/<name>/build/renders/` and described what you saw.
- Warnings are not ignored silently. Fix them, or waive them in `boards/<name>/waivers.yaml`
  with a one-line reason each.

## Rules that are easy to get wrong

- **Pinouts and footprints pass every check even when they're wrong.** For every IC and connector,
  write the datasheet pin table next to the part (comment in the `.ato`) and say in
  your summary that you cross-checked it. Flag anything you could not verify.
- **Prefer JLC Basic / Preferred parts.** Each unique Extended part adds a setup fee
  and stock risk. Report the Basic/Extended split in every BOM summary.
- **Pin critical parts by LCSC ID** (`lcsc_id = "C…"`). Let atopile auto-pick passives only.
  Picked parts are vendored into `parts/` and committed, so builds don't need atopile's API.
- **Respect the assembly tier** chosen in the board spec (Economic vs Standard, see
  `docs/jlcpcb.md`). It changes min package size, sides, and whether panel rails are needed.
- **Units are mm everywhere** in our own code and YAML.
- **Mechanical fit is a check, not a vibe**: when chassis CAD exists, the board STEP must
  pass the interference check in `make check`.

## Git conventions

- One logical change per commit; message says *what changed in the board* and *why*
  (e.g. `bot-main: move IMU to board centroid to reduce vibration coupling`).
- Commit sources and the small, reviewable artifacts (check reports, PNG renders,
  BOM/CPL). Gerber zips and STEP are reproduced from sources, so don't commit them,
  except in a tagged release (`<board>/vX.Y`) that was actually ordered.
- Every order to JLC gets a git tag. The tag is the record of what was built.

## Repo layout

```
CLAUDE.md                 this file
Makefile                  single entry point: make <target> BOARD=<name>
docs/                     pipeline, fab rules, review gates, decisions (ADRs)
toolchain/                pinned tool versions + container definition
tools/                    our Python pipeline code (placement, routing, checks, diff, export)
boards/_template/         copy this to start a new board
boards/<name>/            one self-contained atopile project per board
  spec.md                 requirements, written with the human, and the single source for constraints
  ato.yaml, *.ato, parts/ circuit (atopile)
  mechanical/             outline.py + chassis/ (STEP/SVG/DXF supplied by the human)
  placement.yaml          placement rules
  routing.yaml            critical-net routing + net classes
  waivers.yaml            accepted warnings with reasons
  build/                  generated (mostly gitignored; see .gitignore)
```

## Starting a new board

1. `cp -r boards/_template boards/<name>`
2. Fill `spec.md` **with the human**: ask about anything left as `TBD` that affects
   layout (size, layers, currents, connectors, assembly tier, mechanical envelope).
3. Write the circuit, build, then stop at **review gate 1** (parts and pinouts) before placement.

## Status

Pipeline implementation status lives in `docs/pipeline.md`. Check it before assuming a
`make` target works. Anything marked *planned* must be built and proven before you
rely on it.
