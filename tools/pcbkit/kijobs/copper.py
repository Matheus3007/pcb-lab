"""Export copper geometry per layer and net as polygons, for the layout checks. Runs under KiCad's Python.

usage: kipy copper.py BOARD.kicad_pcb OUT.json ORIGIN_X ORIGIN_Y

{"fills": {layer: {net: [poly]}}, "items": {layer: {net: [poly]}}}: fills are zone fills (as saved, so
run after the stitcher's final fill); items are pads, tracks and vias. poly = [outline, hole, hole...],
each a list of [x, y] in board mm (origin-relative, +Y down).
"""
import json
import sys

import pcbnew

board_path, out, ox, oy = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
b = pcbnew.LoadBoard(board_path)
layers = [l for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
          if l in (pcbnew.F_Cu, pcbnew.B_Cu) or b.GetCopperLayerCount() > 2]
ERR = pcbnew.FromMM(0.01)


def chain(c):
    return [[round(pcbnew.ToMM(c.CPoint(i).x) - ox, 4), round(pcbnew.ToMM(c.CPoint(i).y) - oy, 4)]
            for i in range(c.PointCount())]


def polys(ps):
    res = []
    for i in range(ps.OutlineCount()):
        res.append([chain(ps.Outline(i))] + [chain(ps.Hole(i, h)) for h in range(ps.HoleCount(i))])
    return res


fills = {b.GetLayerName(l): {} for l in layers}
items = {b.GetLayerName(l): {} for l in layers}
for z in b.Zones():
    if z.GetIsRuleArea():
        continue
    for l in layers:
        if z.IsOnLayer(l):
            fills[b.GetLayerName(l)].setdefault(z.GetNetname(), []).extend(polys(z.GetFilledPolysList(l)))

things = list(b.GetTracks()) + list(b.GetPads())
for it in things:
    for l in layers:
        if not it.IsOnLayer(l):
            continue
        if isinstance(it, pcbnew.PAD) and not it.IsOnCopperLayer():
            continue
        ps = pcbnew.SHAPE_POLY_SET()
        it.TransformShapeToPolygon(ps, l, 0, ERR, pcbnew.ERROR_INSIDE)
        items[b.GetLayerName(l)].setdefault(it.GetNetname(), []).extend(polys(ps))

json.dump({"fills": fills, "items": items}, open(out, "w", encoding="utf-8", newline="\n"))
print(f"copper geometry: {sum(len(v) for d in fills.values() for v in d.values())} fill polygons, "
      f"{sum(len(v) for d in items.values() for v in d.values())} item polygons")
