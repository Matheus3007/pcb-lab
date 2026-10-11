"""Add stitching vias for a net on a grid, wherever a via fits entirely inside that net's
filled zones on all copper layers (so it cannot clash with other copper). Runs after
routing. Runs under KiCad's Python.

usage: kipy stitch.py BOARD.kicad_pcb NET PITCH_MM VIA_DIA_MM VIA_DRILL_MM EDGE_MARGIN_MM
"""
import math
import sys

import pcbnew

board_path, net_name = sys.argv[1], sys.argv[2]
pitch, dia, drill, margin = map(float, sys.argv[3:7])
b = pcbnew.LoadBoard(board_path)
net = b.FindNet(net_name)
zones = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == net_name]
layers = [pcbnew.F_Cu, pcbnew.B_Cu] + [l for l in (pcbnew.In1_Cu, pcbnew.In2_Cu) if b.GetCopperLayerCount() > 2]


def fill_of(layer):
    polys = [z.GetFilledPolysList(layer) for z in zones if z.IsOnLayer(layer)]
    return polys


fills = {l: fill_of(l) for l in layers}
if not all(fills.values()):
    raise SystemExit(f"stitch: net {net_name} needs a zone on every copper layer")

r = pcbnew.FromMM(dia / 2 + 0.05)
ring = [(r * math.cos(a), r * math.sin(a)) for a in [i * math.pi / 6 for i in range(12)]] + [(0, 0)]


def fits(x, y):
    for l, polys in fills.items():
        for dx, dy in ring:
            p = pcbnew.VECTOR2I(int(x + dx), int(y + dy))
            if not any(ps.Contains(p) for ps in polys):
                return False
    return True


bb = b.GetBoardEdgesBoundingBox()
step, m = pcbnew.FromMM(pitch), pcbnew.FromMM(margin)
existing = [v.GetPosition() for v in b.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]
added = 0
y = bb.GetY() + m
while y < bb.GetBottom() - m:
    x = bb.GetX() + m
    while x < bb.GetRight() - m:
        if fits(x, y) and all(math.hypot(x - e.x, y - e.y) > step * 0.7 for e in existing):
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
            v.SetWidth(pcbnew.FromMM(dia))
            v.SetDrill(pcbnew.FromMM(drill))
            v.SetNet(net)
            b.Add(v)
            existing.append(v.GetPosition())
            added += 1
        x += step
    y += step

def add_via(x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetWidth(pcbnew.FromMM(dia))
    v.SetDrill(pcbnew.FromMM(drill))
    v.SetNet(net)
    b.Add(v)


# Second pass: every fill island must hold a via or THT pad of the net, otherwise it is
# only tied to its own layer (or floating). Search it on a fine grid for a via spot.
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
anchors = [v.GetPosition() for v in b.GetTracks() if isinstance(v, pcbnew.PCB_VIA) and v.GetNetname() == net_name]
anchors += [p.GetPosition() for p in b.GetPads() if p.GetNetname() == net_name and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
fine = pcbnew.FromMM(0.2)
islands = 0
for l, polys in {l: fill_of(l) for l in layers}.items():
    for ps in polys:
        for i in range(ps.OutlineCount()):
            ol = ps.Outline(i)
            if any(ol.PointInside(a) for a in anchors):
                continue
            box = ol.BBox()
            spot = None
            yy = box.GetY()
            while spot is None and yy < box.GetBottom():
                xx = box.GetX()
                while xx < box.GetRight():
                    if ol.PointInside(pcbnew.VECTOR2I(int(xx), int(yy))) and fits(xx, yy):
                        spot = (xx, yy)
                        break
                    xx += fine
                yy += fine
            if spot:
                add_via(*spot)
                anchors.append(pcbnew.VECTOR2I(int(spot[0]), int(spot[1])))
                islands += 1
            else:
                print(f"stitch: WARNING island on {b.GetLayerName(l)} near "
                      f"({pcbnew.ToMM(box.Centre().x):.1f},{pcbnew.ToMM(box.Centre().y):.1f}) has no room for a via")

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(board_path, b)
print(f"stitch: added {added} grid + {islands} island {net_name} vias")
