---
name: new-board
description: Start a new PCB in pcb-lab. Scaffolds boards/<name> from the template, runs the spec interview with the human, sets board.yaml (layers, assembly tier, quantity), and plans the three review gates. Use when the user asks to design, start or create a new board.
---

# Start a new board

## 1. Scaffold
```bash
cp -r boards/_template boards/<name>          # kebab-case name
```
Add a row to `boards/README.md`. If it belongs to a larger project, link `docs/projects/<project>.md`.

## 2. Spec interview (with the human, before any circuit work)
Fill `boards/<name>/spec.md`. Ask only what's still open, grouped in **one** message:

- **Purpose**: what the board does; what it connects to.
- **Mechanical**: max outline, cutouts, thickness, mounting, height limits per side and region,
  mass budget, chassis CAD (ask for STEP for 3D, SVG/DXF for 2D outline → `mechanical/chassis/`).
- **Electrical**: input source and range, rails and currents, high-current nets (continuous/peak),
  critical signals (USB, SPI, current sense, RF), connectors and mating parts.
- **Environment**: shock/vibration, temperature, moisture (e.g. combat robot → shock first).
- **Fab**: quantity, layers, copper weight, assembly tier (see below), finish/color.

Decide the **assembly tier** early (docs/jlcpcb.md). It constrains placement:
- Economic: one side only, ≥0402, 0.8–1.6 mm thick, board ≥10×10 mm. Cheapest.
- Standard: both sides, 0201, any thickness, but board ≥70×70 mm, so a small board ships as a panel.

Leave every `TBD` that affects layout in "Open questions"; resolve them before gate 2.

## 3. board.yaml
`layers`, `thickness`, `assembly_tier`, `quantity`, `silk_refs` (false on dense boards),
`copper_oz` if not 1, `rules:` overrides only with a reason comment.

## 4. Plan the work as gates (docs/review-gates.md)
1. Circuit + parts (`circuit.py`, new parts via `/add-part`) → `make build` until the circuit validates
   → `/review-gate` 1 → **stop**.
2. Outline (`mechanical/outline.py`) + placement (`placement.yaml` with rules) → `/board-iteration`
   → `/review-gate` 2 → **stop**.
3. Routing (`routing.yaml`) → `/board-iteration` → `/jlc-order` (gate 3) → **stop**.

## Conventions to keep in mind
- Coordinates mm, origin top-left, **+Y down**, rotation CCW (as on screen).
- Reuse `lib/basic_passives.yaml` before searching for passives.
- Look at `boards/pipeline-demo/` as the reference for every file's format.
