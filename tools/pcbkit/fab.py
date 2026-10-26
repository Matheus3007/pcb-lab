"""Stage 7: JLCPCB fabrication + assembly outputs -> build/fab/.

  <board>-gerbers.zip   Gerbers + Excellon drill (upload to JLC "PCB")
  <board>-bom.csv       Comment, Designator, Footprint, LCSC Part #
  <board>-cpl.csv       Designator, Mid X, Mid Y, Layer, Rotation (rotation-corrected)
  cpl_corrections.json  which parts got a rotation/offset correction and from which rule
"""
from __future__ import annotations

import csv
import json
import math
import re
import shutil
import zipfile

from .pipeline import ROOT, Board, kicad_cli, yload

GERBER_LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"


def _gerber_layers(n_copper: int) -> str:
    """Inner copper (In1.Cu..In{n-2}.Cu) must be listed explicitly, or a 4-layer board ships as 2 layers."""
    return ",".join([f"In{i}.Cu" for i in range(1, n_copper - 1)] + [GERBER_LAYERS])


def _rotations():
    """Our confirmed corrections first (lib/jlc_rotations_confirmed.csv), then community hints."""
    rows = []
    for name in ("jlc_rotations_confirmed.csv", "jlc_rotations.csv"):
        rows += _read_rotations(ROOT / "lib" / name, confirmed=name.endswith("confirmed.csv"))
    return rows


def _read_rotations(path, confirmed):
    rows = []
    if not path.exists():
        return rows
    with open(path, newline="") as f:
        for r in csv.reader(line for line in f if not line.startswith("#")):
            if not r or r[0].startswith("Footprint"):
                continue
            # "lcsc:C123" keys a rule to the LCSC part (JLC rotates by the part's EasyEDA model, which can
            # differ between parts on the same footprint); anything else is a footprint-name regex
            rows.append((re.compile(r[0].strip()), float(r[1]),
                         float(r[2]) if len(r) > 2 and r[2].strip() else 0.0,
                         float(r[3]) if len(r) > 3 and r[3].strip() else 0.0, confirmed))
    return rows


def fab(name: str) -> dict:
    b = Board(name)
    out = b.fab
    tmp = b.work / "gerbers"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    n_copper = int(yload(b.dir / "board.yaml").get("layers", 2))
    kicad_cli("pcb", "export", "gerbers", "-o", tmp, "--layers", _gerber_layers(n_copper),
              "--subtract-soldermask", "--check-zones", "--use-drill-file-origin", b.pcb)
    kicad_cli("pcb", "export", "drill", "-o", tmp, "--format", "excellon", "--excellon-units", "mm",
              "--drill-origin", "plot", "--excellon-separate-th", b.pcb)
    copper = [f.name for f in tmp.iterdir() if re.search(r"_Cu\.g", f.name)]
    if len(copper) != n_copper:
        raise SystemExit(f"fab: {len(copper)} copper gerbers for a {n_copper}-layer board: {sorted(copper)}")
    zpath = out / f"{name}-gerbers.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(tmp.iterdir()):
            z.write(f, f.name)

    # --- BOM (from the circuit, so values/LCSC IDs come from source, not the board)
    netlist = json.loads((b.work / "netlist.json").read_text())
    groups: dict[str, dict] = {}
    for p in netlist["parts"]:
        if p["dnp"]:
            continue
        g = groups.setdefault(p["lcsc"], {"Comment": p["value"], "Designator": [],
                                          "Footprint": p["footprint"].split(":")[1], "LCSC Part #": p["lcsc"]})
        g["Designator"].append(p["ref"])
    with open(out / f"{name}-bom.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Comment", "Designator", "Footprint", "LCSC Part #"])
        w.writeheader()
        for g in groups.values():
            w.writerow({**g, "Designator": ",".join(sorted(g["Designator"], key=lambda r: (r[0], int(re.sub(r"\D", "", r) or 0))))})

    # --- CPL: positions relative to the aux (board) origin, JLC rotation corrections
    pos = b.work / "pos.csv"
    kicad_cli("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
              "--exclude-dnp", "--use-drill-file-origin", "-o", pos, b.pcb)
    rules = _rotations()
    lcsc_of = {p["ref"]: p["lcsc"] for p in netlist["parts"]}
    corrections = []
    with open(pos, newline="") as f, open(out / f"{name}-cpl.csv", "w", newline="") as g:
        w = csv.writer(g)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in csv.DictReader(f):
            fpname = r["Package"]
            rot, x, y = float(r["Rot"]), float(r["PosX"]), float(r["PosY"])
            for rx, drot, dx, dy, confirmed in rules:
                key = rx.pattern
                hit = (key[5:] == lcsc_of.get(r["Ref"])) if key.startswith("lcsc:") else rx.search(fpname)
                if hit:
                    rot = (rot + drot) % 360
                    a = math.radians(float(r["Rot"]))
                    x += dx * math.cos(a) - dy * math.sin(a)
                    y += dx * math.sin(a) + dy * math.cos(a)
                    corrections.append({"ref": r["Ref"], "footprint": fpname, "rule": rx.pattern,
                                        "rotation_delta": drot, "offset": [dx, dy],
                                        "source": "confirmed" if confirmed else "community hint (unverified)"})
                    break
            layer = "Top" if r["Side"].lower() == "top" else "Bottom"
            w.writerow([r["Ref"], f"{x:.4f}mm", f"{y:.4f}mm", layer, f"{rot:g}"])
    (out / "cpl_corrections.json").write_text(json.dumps(corrections, indent=1) + "\n")
    return {"gerbers": zpath.name, "bom_lines": len(groups), "cpl_corrections": corrections}
