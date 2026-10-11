# Toolchain

Pinned versions: `versions.env`. Phase 0 decides between:
1. **Container** (preferred, reproducible): KiCad 10 + Python 3.14/atopile + Java/Freerouting.
   Docker Desktop's WSL integration must be enabled for this distro (currently `docker` is not on PATH in WSL).
2. **Native fallback**: Windows `kicad-cli.exe` (`/mnt/c/Program Files/KiCad/10.0/bin/`) + `uv`-managed Python 3.14 in WSL.

Also lives here: `jlc-economic.kicad_dru`, `jlc-standard.kicad_dru` (DRC rules generated from docs/jlcpcb.md, planned).
atopile telemetry must be disabled (`~/atopile/telemetry.yaml: telemetry: false`).
