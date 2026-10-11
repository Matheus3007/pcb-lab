"""Dump a board to JSON for custom checks and semantic diffs. Runs under KiCad's Python.

usage: kipy dump.py BOARD.kicad_pcb OUT.json ORIGIN_X ORIGIN_Y
Coordinates are written in board mm (origin-relative, +Y down), rounded to 1 µm.
"""
import json
import sys

import pcbnew

board_path, out, ox, oy = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
b = pcbnew.LoadBoard(board_path)


def xy(v):
    return [round(pcbnew.ToMM(v.x) - ox, 3), round(pcbnew.ToMM(v.y) - oy, 3)]


def box(bb):
    return [*xy(bb.GetOrigin()), *xy(bb.GetEnd())]


fps = []
for fp in b.GetFootprints():
    crt = fp.GetCourtyard(fp.GetLayer())
    cbox = crt.BBox() if crt.OutlineCount() else fp.GetBoundingBox(False)
    fps.append({
        "ref": fp.GetReference(), "value": fp.GetValue(),
        "footprint": fp.GetFPID().GetUniStringLibId(),
        "at": xy(fp.GetPosition()), "rot": round(fp.GetOrientationDegrees(), 2),
        "side": "bottom" if fp.IsFlipped() else "top",
        "dnp": fp.IsDNP(), "courtyard": box(cbox),
        "smd": all(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD for p in fp.Pads()) and len(fp.Pads()) > 0,
        "pads": sorted(({"num": p.GetNumber(), "net": p.GetNetname(), "at": xy(p.GetPosition())}
                        for p in fp.Pads()), key=lambda p: (p["num"], p["at"])),
    })

tracks, vias = [], []
for t in b.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA):
        vias.append({"net": t.GetNetname(), "at": xy(t.GetPosition()),
                     "diameter": round(pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)), 3),
                     "drill": round(pcbnew.ToMM(t.GetDrillValue()), 3)})
    else:
        tracks.append({"net": t.GetNetname(), "layer": t.GetLayerName(),
                       "width": round(pcbnew.ToMM(t.GetWidth()), 3),
                       "length": round(pcbnew.ToMM(t.GetLength()), 3),
                       "start": xy(t.GetStart()), "end": xy(t.GetEnd())})

tracks.sort(key=lambda t: (t["net"], t["layer"], t["start"], t["end"]))
vias.sort(key=lambda v: (v["net"], v["at"]))
edge = b.GetBoardEdgesBoundingBox()
nets = {}
for t in tracks:
    n = nets.setdefault(t["net"], {"track_length": 0.0, "min_width": None, "segments": 0})
    n["track_length"] = round(n["track_length"] + t["length"], 3)
    n["min_width"] = t["width"] if n["min_width"] is None else min(n["min_width"], t["width"])
    n["segments"] += 1
for v in vias:
    nets.setdefault(v["net"], {"track_length": 0.0, "min_width": None, "segments": 0})
    nets[v["net"]]["vias"] = nets[v["net"]].get("vias", 0) + 1

json.dump({
    "board_bbox": box(edge),
    "size_mm": [round(pcbnew.ToMM(edge.GetWidth()), 3), round(pcbnew.ToMM(edge.GetHeight()), 3)],
    "layers": b.GetCopperLayerCount(),
    "footprints": sorted(fps, key=lambda f: f["ref"]),
    "nets": dict(sorted(nets.items())),
    "totals": {"tracks": len(tracks), "vias": len(vias),
               "track_length": round(sum(t["length"] for t in tracks), 2)},
    "tracks": tracks, "vias": vias,
}, open(out, "w", encoding="utf-8", newline="\n"), indent=1)
print(f"dumped {len(fps)} footprints, {len(tracks)} tracks, {len(vias)} vias")
