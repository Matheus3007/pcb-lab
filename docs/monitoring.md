# Watching a board in VS Code

Open the repo in VS Code **through WSL** (`code /mnt/c/Users/mathe/pcb-lab` from the WSL
shell, or "WSL: Open Folder in WSL"). Accept the recommended extensions when prompted (they are
listed in `.vscode/extensions.json`).

| What | Where | How |
|---|---|---|
| **Dashboard** (renders + checks + BOM) | `boards/<name>/build/review/index.html` | right-click → **Show Preview** (Live Preview). Refreshes on every `make all`. |
| Check summary | `boards/<name>/build/reports/summary.md` | Markdown preview (`Ctrl+Shift+V`) |
| Review packets | `boards/<name>/build/review/gate-N.md` | Markdown preview (images inline) |
| Renders | `boards/<name>/build/renders/*.png` | click to open; pin the tab |
| **Interactive 3D** | `boards/<name>/build/work/<name>.glb` | opens in the GLB viewer (rotate/zoom) |
| Interactive board | `boards/<name>/build/work/<name>.kicad_pcb` | `make open BOARD=<name>` (KiCad PCB editor, Alt+3 for 3D), or the KiCad Viewer extension. Look only: the file is regenerated every build. |
| Diff vs last commit | `boards/<name>/build/work/diff.md` | after `make diff BOARD=<name>` |

Run anything yourself from **Terminal → Run Task** (or `Ctrl+Shift+B` for `make all`):
`pcb: all`, `pcb: check`, `pcb: fab outputs`, `pcb: review packet`, `pcb: diff`, `pcb: parts`.

Committed history of every result lives in git: `build/reports/`, `build/renders/` and
`build/review/` are versioned, so the GitHub/VS Code diff of a commit shows the renders changing.
