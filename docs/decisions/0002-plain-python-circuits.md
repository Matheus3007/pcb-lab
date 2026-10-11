# 0002: Plain-Python circuits instead of atopile

Date: 2026-10-11 · Status: accepted · Supersedes the "Circuit" part of 0001

## Context
While setting up Phase 0, atopile 0.15.9 turned out to be end-of-life as a local tool:
- its CLI prints that 0.15.8 is the last CLI release, in maintenance mode, replaced by the
  hosted app at app.atopile.io (0.16+);
- part picking now raises "Part picking on atopile 0.15.8 requires sign-in";
- both service domains (components.atopileapi.com, packages.atopileapi.com) did not resolve
  on 2026-10-11, so picking and the package registry fail outright.

The owner's requirement is a fully local, git-versioned loop with no accounts.

## Decision
Circuits are plain Python (`boards/<name>/circuit.py`, using `tools/pcbkit/circuit.py`):
- parts pinned by LCSC ID; ICs/connectors defined once in `lib/parts.yaml` with the
  datasheet evidence for their pin mapping; generic passives via `Circuit.passive()`;
- footprints from KiCad's stock library first; LCSC/EasyEDA conversions (easyeda2kicad)
  only when KiCad has nothing, and always checked against the KiCad/datasheet geometry;
- JLC tier/stock/price from JLC's public parts-search endpoint, cached in `lib/jlc_cache.json`;
- design intent as numeric assertions (`Circuit.check`) and electrical rules (`validate()`);
- the .kicad_pcb is regenerated from scratch on every build by KiCad's own Python (pcbnew).

## Consequences
- No vendor service in the loop except JLC's own catalog (needed anyway to order).
- No parametric auto-picking: the agent picks parts and must justify them at gate 1.
- No schematic: electrical checking = `validate()` + assertions + gate-1 review.
