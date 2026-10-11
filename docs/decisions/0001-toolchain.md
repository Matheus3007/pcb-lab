# 0001: Toolchain: atopile + KiCad 10 + scripted geometry/placement + Freerouting

Date: 2026-10-11 · Status: accepted; circuit tool superseded by 0002 (atopile → plain Python)

## Context
We want PCBs fully described as code so an agent can edit → build → check → look → iterate,
with git as the history, ending in JLCPCB assembled orders. The human reviews results, not code.

## Decision
- **Circuit: atopile** (MIT, runs locally). Declarative, units and tolerances, assertions,
  parametric part picking from the JLC/LCSC catalog, picked parts vendored into the repo.
  Benchmark evidence (EEBench, run by atopile's authors, so treat with care) shows Claude
  agents work well in it.
- **Engine: KiCad 10** via `kicad-cli` (DRC JSON with exit codes, Gerber/drill/pos/STEP,
  SVG/3D renders). No GUI in the loop.
- **Geometry and placement: our own Python**, because atopile does not model board shape and the
  target boards are mechanically constrained (custom outlines/cutouts, chassis fit).
- **Routing: scripted critical nets + Freerouting** (headless, DSN/SES via KiCad's Python).

## Rejected
- **SKiDL**: KiCad 9/10 support unclear; netlist/symbol friction reported on KiCad 9.
- **tscircuit**: promising, but as of 2026 open defects hit fab directly (autorouter
  emitting blind/buried vias on 4-layer, routed paths dropped on export, KiCad export
  failing LVS in third-party tests).
- **KiCad IPC API (kicad-python)**: requires a running GUI; not usable headless.
- **Plain Python netlist generation**: viable, but more homegrown code and no part
  picking/assertions. Fallback if atopile becomes unusable.

## Risks
- atopile is pre-1.0 (core rewrite Jan 2026, needs Python 3.14). We pin versions.
- Part picking depends on atopile's hosted API. Mitigation: pin critical parts by LCSC ID,
  commit `parts/`. Worst case: fork/run locally (MIT).
- No schematic means no KiCad ERC. Mitigation: assertions + custom net checks + gate 1.
- Autorouting quality. Mitigation: script critical nets, review renders.
