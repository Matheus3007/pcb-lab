# Third-party material

Everything committed in this repo is MIT-licensed (see `LICENSE`). Material under other or unclear
licenses is **not committed**: `toolchain/third_party.sh` (run by `make toolchain`) downloads it at a
pinned version and verifies it against `toolchain/third_party.sha256`.

| File (gitignored) | Source | License |
|---|---|---|
| `lib/jlc_rotations.csv` | [matthewlai/JLCKicadTools](https://github.com/matthewlai/JLCKicadTools) `cpl_rotations_db.csv` @ `50ab537` | GPL-3.0 |
| `lib/3d/HRO_TYPE-C-31-M-12_C165948.step` | LCSC/EasyEDA model for C165948, via easyeda2kicad | EasyEDA/LCSC terms (unclear) |
| `lib/datasheets/` | JLCPCB/LCSC datasheet downloads (`make part`) | manufacturers' copyright |

Used at run time, not distributed: KiCad 10 (GPL-3.0, incl. its symbol/footprint/3D libraries, which
carry a CC-BY-SA 4.0 + exception license), Freerouting (GPL-3.0), Eclipse Temurin JRE (GPLv2 + CE).

`lib/jlc_rotations_confirmed.csv` is ours: corrections verified in JLC's preview.

Generated schematics embed copies of KiCad library symbols. The KiCad library license explicitly allows
using them in your own designs without that license applying to the design.
