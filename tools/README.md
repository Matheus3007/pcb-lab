# tools/

Our pipeline code (Python). Planned modules, built in Phase 0:

| Module | Stage |
|---|---|
| `outline.py` | write Edge.Cuts/cutouts/holes/keepouts from `mechanical/outline.py` |
| `place.py` | apply `placement.yaml` to the `.kicad_pcb` (idempotent) |
| `route.py` | critical-net routing from `routing.yaml`, Freerouting DSN/SES round trip |
| `checks/` | custom checks → JSON (decoupling distance, current vs width, BOM tiers, edge, height, CPL) |
| `render.py` | SVG/PNG layer renders + 3D renders |
| `diff.py` | semantic board diff between git refs + side-by-side renders |
| `fab.py` | JLC BOM/CPL (rotation corrections), gerber zip, review packets |

Conventions: units mm; every tool is a CLI that writes JSON and exits non-zero on failure;
no tool reads anything outside its board directory except `toolchain/` and `docs/jlcpcb.md`-derived rules.
