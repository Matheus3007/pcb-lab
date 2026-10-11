# Toolchain

`./setup.sh` (or `make toolchain`) installs everything without sudo on WSL2:

| Piece | Where | Why |
|---|---|---|
| KiCad 10 (prereq) | Windows `C:\Program Files\KiCad\10.0` | engine: pcbnew Python, kicad-cli |
| `bin/kicad-cli` | wrapper | runs kicad-cli.exe with WSL→Windows path translation |
| `bin/kipy` | wrapper | runs a script under KiCad's Python (pcbnew) with repo paths injected |
| `bin/freerouting` | wrapper | headless Freerouting on Temurin JRE (`~/.local/opt`) |
| `.venv/` | uv venv (Python 3.12) | WSL-side tools: easyeda2kicad, cairosvg, pymupdf, shapely, yaml |
| `.kipy-site/` | pip --target for KiCad's Python | pyyaml, shapely (KiCad's own numpy is used) |
| `rules/jlc.yaml` | design rules per layer count + assembly-tier limits | from docs/jlcpcb.md |

Versions are pinned in `versions.env`. Bump one at a time, in its own commit, and re-run
`make all` on every board.
