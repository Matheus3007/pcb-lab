---
name: add-part
description: Research, verify and add a part (IC, connector, sensor, MOSFET, anything beyond a basic R/C/LED) to lib/parts.yaml in pcb-lab, with datasheet pinout evidence, a checked footprint and a 3D model. Use whenever a circuit needs a part that is not already in lib/parts.yaml or lib/basic_passives.yaml.
---

# Add a part

A wrong pinout or footprint passes every automated check. This procedure is the defense; don't skip steps.

## 1. Pick the LCSC part
- Prefer JLC **Basic**, then **Preferred ("promotional") Extended**, then plain Extended (per-part setup
  fee). `make part` shows the tier. A plain Extended part needs `extended_reason:` in its parts.yaml
  entry saying why no Basic/Preferred alternative works. Check stock ≥ 10× what you need.
- Passives first come from `lib/basic_passives.yaml`; if missing, find a Basic one and add it there after a lookup.
- Beware clones: the same MPN from a different manufacturer can have a **different pinout**.

## 2. Research
```bash
make part LCSC=C12345
```
Prints manufacturer/MPN, tier, stock, price; downloads the datasheet (JLC file endpoint) to
`lib/datasheets/C12345.pdf`; extracts the pages with pin tables as text **and** PNG
(`lib/datasheets/C12345_pN.png`); lists KiCad stock footprint candidates.

**Open the page PNGs with Read** (the Read tool can't render PDFs here). Text extraction scrambles
tables; use the image to read pin number → name for the exact package. If no pin page was found, render more
pages: `python -c "import pymupdf; d=pymupdf.open('lib/datasheets/C12345.pdf'); d[N].get_pixmap(dpi=110).save('p.png')"`
(using `toolchain/.venv/bin/python`).

## 3. Footprint
Prefer the KiCad stock footprint matching the package exactly (pitch, body size, pad count, EP).
```bash
make footprint FP=Package_DFN_QFN:QFN-48-1EP_7x7mm_P0.5mm_EP5.6x5.6mm
```
Gives the pad table, fab/courtyard extents, a facing hint for connectors, 3D-model presence and a PNG
(`lib/datasheets/fp/<name>.png`, look at it). Check:
- pad count and numbering match the datasheet's package drawing (pin 1 corner, numbering direction, EP number);
- the datasheet's **recommended land pattern** is close to the footprint pads;
- for connectors: which side the mouth/cable faces at rot 0 (note it in parts.yaml `notes`).

No suitable stock footprint? (`source toolchain/env.sh` first) `easyeda2kicad --footprint --3d --lcsc_id C12345 --output lib/footprints/<Lib>`
(rename/move so it's `lib/footprints/<Lib>.pretty/<Name>.kicad_mod`), then inspect it with
`make footprint` exactly like a stock one. EasyEDA conversions are "no guarantee".

## 4. 3D model
If `make footprint` says MISSING: (`source toolchain/env.sh`) `easyeda2kicad --3d --lcsc_id C12345 --output <tmp>`; copy the STEP to
`lib/3d/<MPN>_<LCSC>.step`. Work out the offset by comparing pad coordinates of the EasyEDA footprint
(in the same output) with the KiCad footprint: `offset = (dx, -dy, 0)` because model Y is up while
footprint Y is down. Usually also `rotate: [0, 0, 180]` (check the EasyEDA `.kicad_mod` model block).
Confirm in `3d_iso.png` after the next `make all`: the body must sit on its pads.

## 5. lib/parts.yaml entry
```yaml
MPN-or-short-key:
  lcsc: C12345
  value: short label for BOM
  footprint: Lib:Name
  pins: {VDD: [1, 8], GND: [4, EP], SDA: 5, SCL: 6, NC1: 2}   # every pad covered; group same-net pads
  pinout_source: "<Mfr> <doc id/rev> p.<n> <table name>, <package> column"
  pinout_verified: YYYY-MM-DD
  model: {path: lib/3d/..., offset: [x, y, z], rotate: [0, 0, r]}   # only if KiCad has none
  notes: "facing, clone warnings, abs-max ratings that matter, required external parts"
```
Every pad must appear in `pins` (unused ones too: give them names and `c.nc(...)` them in the circuit), or
`validate()` can't catch an unconnected pin.

## 6. Note the electrical requirements
Write the datasheet's required external parts (decoupling values, pull-ups, bootstrap caps, max Vin)
into `notes`, then express them in `circuit.py` as parts **and** as `c.check(...)` assertions.

## 7. Record a lesson if anything surprised you
Add a line to CLAUDE.md under "Hard-won lessons" (e.g. a clone pinout or an odd footprint origin).
