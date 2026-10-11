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
- **Routing: no unneeded bends.** Every bend, jog (short sideways step) and detour adds length, loop
  area and impedance discontinuities, i.e. noise. Prefer straight runs and 45° transitions; never accept
  a jog or a loop around a part when a direct path exists. Enforced by: best-of-N autorouting scored on
  jogs/vias/bends/length (`routing.yaml autoroute.attempts`), the jog straightener (`kijobs/straighten.py`),
  and the `routing/jog` check (warning: fix it or waive it with a reason). Sensitive nets (motor phases,
  current sense, IMU SPI, USB) get scripted tracks in `routing.yaml`, never the autorouter.
- **Part tier priority: JLC Basic > Preferred ("promotional") Extended > plain Extended**, where viable.
  Basic and Preferred parts have no per-part setup fee and are always loaded on the machines. A plain
  Extended part needs `extended_reason:` in parts.yaml (the `parts/extended` check warns otherwise).
- **Prefer JLC Basic / Preferred parts.** `make parts BOARD=x` shows the tier, stock and price;
  `make part LCSC=C...` researches a new part; `make footprint FP=Lib:Name` inspects a footprint.
- **3D models**: if KiCad has no model, fetch one (easyeda2kicad), re-origin it via
  `model.offset` in parts.yaml, and confirm alignment in `3d_iso.png`. Missing models make
  the mechanical-fit checks blind.
- **Assembly tier** (board.yaml `assembly_tier`) drives side/package/size checks.
- **Coordinates**: mm, board origin top-left, **+Y down** (KiCad convention), rotations CCW.
- **CPL rotations**: `lib/jlc_rotations_confirmed.csv` (ours, verified in JLC's preview) is checked first,
  then `lib/jlc_rotations.csv` (community hints, often outdated: its HRO USB-C +180 and SOT-23 −90 were
  both wrong in JLC's 2026 preview; confirmed: HRO USB-C 0° + 1.575 mm, KiCad SOT-23 180°). JLC places
  parts from the EasyEDA footprint origin, so a connector whose KiCad origin differs needs an offset.
  The human confirms every part at gate 3. The 2D close-up in JLC's preview is the clearest view; 3D is ambiguous.

## Skills (use them; they encode the procedures below)

| Skill | When |
|---|---|
| `/new-board` | starting a board: scaffold, spec interview, gate plan |
| `/add-part` | adding any IC/connector/non-trivial part to `lib/parts.yaml` |
| `/board-iteration` | every edit → build → check → look → fix cycle, incl. a DRC-fix playbook |
| `/review-gate` | producing a gate packet and stopping for the human |
| `/jlc-order` | final fab outputs, order checklist, tagging |

## Hard-won lessons (read before debugging anything)

Environment and tools:
- **KiCad's Windows Python ignores `PYTHONPATH`.** `toolchain/bin/kipy` injects `tools/` and
  `toolchain/.kipy-site` into `sys.path` itself. Install extra KiCad-side deps with
  `pip --target toolchain/.kipy-site`, never into Program Files, and delete numpy from there
  (KiCad's own numpy must win).
- Windows executables need Windows paths: the wrappers convert absolute `/mnt/...` and `/tmp/...`
  args with `wslpath -w`. Any new wrapper or job argument must go through the same conversion.
- **KiCad 10 `kicad-cli` has no DSN/SES commands.** Use `pcbnew.ExportSpecctraDSN(board, path)`
  and `pcbnew.ImportSpecctraSES(board, path)` (kijobs/specctra.py).
- **`pcbnew.SaveBoard()`** writes the `.kicad_pro` too, which net classes need; `board.Save()` doesn't.
- `fp.SetField(k, v)` creates a **visible field on silkscreen**: always `GetField(k).SetVisible(False)`.
- Zones: use `ZONE_CONNECTION_THT_THERMAL` (SMD pads solid). Full thermals on small SMD pads
  give `starved_thermal` DRC errors. `ISLAND_REMOVAL_MODE_ALWAYS` removes floating copper only;
  an island touching a pad of the net stays, so the stitcher adds a via to each such island.
- **Freerouting is deterministic for a given DSN file but sensitive to item ORDER**, and KiCad's DSN
  export shuffles component/net/pin order on every run. The pipeline puts the DSN in canonical (sorted)
  order and then applies a seeded permutation per attempt, so best-of-N routing is both varied and
  reproducible. The lock fingerprint is the canonical form minus the `(parser ...)` header. The DSN line
  `(string_quote ")` contains a lone quote that breaks naive tokenizers.
- Freerouting leaves jogs on most attempts; `kijobs/straighten.py` cuts them like KiCad's optimizer
  (shorten both parallel runs, bridge with one segment, KiCad collision check). In KiCad's Python, never
  hold SWIG track wrappers across board edits: snapshot plain data, look items up by UUID, use `b.Delete()`.
- Freerouting has built-in analytics: the wrapper passes `--usage_and_diagnostic_data.disable_analytics=true`.
- The repo lives on NTFS (`core.fileMode=false`): new scripts need
  `git update-index --chmod=+x <file>` or they're non-executable in clones.
- KiCad's Windows Python writes CRLF unless you `open(..., newline="\n")`; committed reports must be LF.
- Committed artifacts must be stable across identical builds: the DRC report has its `date` and
  per-item `uuid` stripped; renders are only replaced when pixels change visibly
  (antialiasing and ray-tracer noise otherwise churn git); the dashboard HTML is untracked.
- **Windows KiCad auto-updates** (10.0.5 → 10.0.7 on 2026-10-11). After an update, run `make all` on every
  board and update `toolchain/versions.env`. The route-lock fingerprint ignores the DSN `(parser ...)`
  header (host_version), so updates alone don't force reroutes.
- To view a board in the GUI use `make open BOARD=x`. KiCad's project manager reopens whatever project
  the user had last (e.g. their own `Documents\KiCad Projects\...`), which looks like "a blank PCB".
  The pcbnew-written `.kicad_prl` can hide everything in the GUI, so the build deletes it.
- **Gerbers, drill and CPL must share the aux origin** (the builder puts it at the outline's bottom-left).
  Otherwise JLC's preview says "component may be offset" and auto-aligns. Don't ship drill-map
  files in the zip (JLC shows them as an extra layer).
- THT pads that anchor into a pour (connector shields) can get `starved_thermal` after a reroute: set
  `zone_connection: {SH: full}` on the part in parts.yaml (applied per pad by the builder).
- WSL has no sudo password: everything installs to `~/.local` (uv, JRE) or the repo.

Parts and data:
- **atopile is dead locally** (decision 0002). Don't reintroduce it.
- **JLC catalog**: `POST https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList`
  `{"keyword": "<LCSC>"}` works anonymously. `componentLibraryType`: `base` = Basic, `expand` = Extended;
  `preferredComponentFlag` = Preferred Extended.
- **Datasheets**: LCSC's `datasheet` URLs and manufacturer sites (e.g. Torex) return HTML or 403.
  `https://jlcpcb.com/api/file/downloadByFileSystemAccessId/<dataManualFileAccessId>` returns the real PDF
  (`make part` does this). The Read tool can't render PDFs here (no poppler): use the page PNGs from `make part`.
- **Clones have different pinouts** (Torex XC6206: 1=VSS 2=VOUT 3=VIN; UMW's documented
  "XC6206P332MR" differs). Always verify the exact manufacturer behind the LCSC ID.
- Verified Basic passives live in `lib/basic_passives.yaml`. Reuse them before searching.
- KiCad stock 3D models are incomplete (e.g. no model for `USB_C_Receptacle_HRO_TYPE-C-31-M-12`).
  easyeda2kicad models use EasyEDA's footprint origin: compare pad coordinates of both footprints to get
  `model.offset` (Y is up in model space, down in footprint space). That connector needed `[0, 1.575, 0]`, rot 180.
- `MountingHole_*` and other parts with no pins: `pins: {}` in parts.yaml, `dnp: true`.

Geometry and placement:
- KiCad SOT-23-3 at rot 0: pads 1 (−1.14, −0.95), 2 (−1.14, +0.95), 3 (+1.14, 0). Pin 3 is alone on the right.
- HRO TYPE-C-31-M-12 at rot 0: SMD pads at −Y, mouth at +Y. Rot 180 = mouth up (to the top edge),
  and the footprint origin is 3.65 mm behind the mouth.
- `PinHeader_1xNN` at rot 90: pins run +X from pin 1.
- Rotation is CCW on screen (+Y down): a +Y-pointing feature at rot 90 points +X.
- JLC Standard PCBA needs a board of at least 70×70 mm (otherwise a panel); Economic is one-sided
  and 0402 minimum. Check `assembly_tier` before placing anything on the bottom.

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
lib/basic_passives.yaml   verified JLC Basic passives (R/C/LED by size and value)
lib/datasheets/           downloaded by `make part` (gitignored)
lib/3d/, lib/footprints/  models/footprints KiCad doesn't ship
lib/jlc_cache.json        JLC catalog cache   lib/jlc_rotations.csv  CPL corrections
boards/_template/         copy to start a board
boards/<name>/            spec.md, board.yaml, circuit.py, mechanical/, placement.yaml, routing.yaml, waivers.yaml
  build/reports|renders|review   committed results   build/work|fab   generated, ignored
docs/                     pipeline, jlcpcb, review gates, monitoring, decisions, projects
.claude/skills/           project skills (new-board, add-part, board-iteration, review-gate, jlc-order)
.vscode/                  extensions, tasks (Ctrl+Shift+B = make all), viewer settings
```

## Starting a new board

1. `cp -r boards/_template boards/<name>`, then fill `spec.md` **with the human**.
2. Write `circuit.py` (+ new parts in `lib/parts.yaml` with pinout evidence) → `make build` until
   the circuit validates → `make gate GATE=1` and **stop for review**.
3. Outline + placement → `make all` until clean → `make gate GATE=2` and **stop**.
4. Routing → `make all` until clean → `make fab` → `make gate GATE=3` and **stop**.
