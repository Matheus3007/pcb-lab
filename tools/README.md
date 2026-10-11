# tools/pcbkit

Pipeline code. Entry point: `python -m pcbkit <command> <board>` (use the Makefile).
See docs/pipeline.md for the data flow.

| Module | Runs in | Does |
|---|---|---|
| `circuit.py` | WSL venv | circuit model, validation, assertions, netlist.json |
| `pipeline.py` | WSL venv | stage orchestration, kipy/kicad-cli helpers |
| `kijobs/build_board.py` | KiCad Python | generate .kicad_pcb from the job JSON |
| `kijobs/specctra.py` | KiCad Python | DSN export / SES import for Freerouting |
| `kijobs/stitch.py` | KiCad Python | GND stitching vias (grid + orphan islands) |
| `kijobs/dump.py` | KiCad Python | board → JSON for checks and diffs |
| `checks.py` | WSL venv | DRC + custom checks → checks.json, summary.md |
| `render.py` | WSL venv | 2D/3D renders, GLB |
| `fab.py` | WSL venv | gerbers zip, JLC BOM/CPL with rotation corrections |
| `report.py` | WSL venv | dashboard HTML, gate packets |
| `diff.py` | WSL venv | semantic + visual diff vs a git ref |
| `jlc.py` | WSL venv | JLC catalog lookups (cached in lib/jlc_cache.json) |

Conventions: units mm; every stage writes JSON; failures raise `StageError` (exit 1).
