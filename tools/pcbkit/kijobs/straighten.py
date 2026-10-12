"""Remove routing jogs: a short sideways step S between two parallel segments A and C.

Like KiCad's interactive optimizer, the corner is cut instead of re-routing the whole kink:
A is shortened by da before the step, C by dc after it, and one straight bridge joins them. The
bridge is always at exactly 45 degrees to A and C (so a 0/45/90-degree route stays on that grid:
an earlier version bridged at any angle and left crooked traces): its run along A equals the
sideways offset h, i.e. da + dc = h - (the step's own along-A length). Splits from balanced to
lopsided are tried; the first bridge that clears every other-net pad, track and via (KiCad
collision shapes + clearances) and stays inside the outline minus the copper-edge clearance wins.
Runs under KiCad's Python; deterministic.

usage: kipy straighten.py BOARD.kicad_pcb GEOMETRY.json ORIGIN_X ORIGIN_Y EDGE_CLEARANCE_MM
"""
import json
import math
import sys
import time
from collections import defaultdict

import pcbnew
from shapely.geometry import LineString, Polygon

board_path, geo_path = sys.argv[1], sys.argv[2]
ox, oy, edge_clr = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
T0 = time.time()
b = pcbnew.LoadBoard(board_path)
geo = json.load(open(geo_path, encoding="utf-8"))
outline = Polygon(geo["outline"])
for c in geo.get("cutouts", []):
    outline = outline.difference(Polygon(c))

PARALLEL_DEG, JOG_MAX_MM = 5.0, 1.5
SPLITS = [0.5, 0.25, 0.75, 0.0, 1.0]   # share of the needed along-run taken from A (rest from C)
NM = pcbnew.FromMM(1)


def V(x, y):
    return pcbnew.VECTOR2I(int(round(x)), int(round(y)))


def tracks():
    """Fresh snapshot as plain data: never keep SWIG wrappers across edits."""
    out = []
    for t in b.GetTracks():
        if type(t) is pcbnew.PCB_TRACK and t.GetLength() > 0:
            s, e = t.GetStart(), t.GetEnd()
            out.append({"uuid": t.m_Uuid.AsString(), "net": t.GetNetCode(), "layer": t.GetLayer(),
                        "s": (s.x, s.y), "e": (e.x, e.y), "w": t.GetWidth()})
    return out


def by_uuid(u):
    for t in b.GetTracks():
        if t.m_Uuid.AsString() == u:
            return t
    return None


def ang(p, q):
    return math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))


def adiff(a, c):
    d = abs(a - c) % 360
    return min(d, 360 - d)


def obstacles(net, layer):
    obs = []
    for t in b.GetTracks():
        if t.GetNetCode() != net and t.IsOnLayer(layer):
            obs.append((t.GetEffectiveShape(layer), t.GetOwnClearance(layer)))
    for p in b.GetPads():
        if p.GetNetCode() != net and p.IsOnLayer(layer):
            obs.append((p.GetEffectiveShape(layer), p.GetOwnClearance(layer)))
    return obs


inner = {}


def fits(p, q, width, net, layer, obs):
    probe = pcbnew.PCB_TRACK(b)
    probe.SetStart(V(*p))
    probe.SetEnd(V(*q))
    probe.SetWidth(width)
    probe.SetLayer(layer)
    probe.SetNetCode(net)
    shape, own = probe.GetEffectiveShape(layer), probe.GetOwnClearance(layer)
    if any(shape.Collide(o, max(own, c)) for o, c in obs):
        return False
    half = width / NM / 2
    if half not in inner:
        inner[half] = outline.buffer(-(edge_clr + half))
    seg = LineString([(p[0] / NM - ox, p[1] / NM - oy), (q[0] / NM - ox, q[1] / NM - oy)])
    return inner[half].covers(seg)


def toward(p, q, dist):
    """Point at `dist` (nm) from p toward q, clamped to q."""
    L = math.dist(p, q)
    if L == 0 or dist >= L:
        return q
    return (p[0] + (q[0] - p[0]) * dist / L, p[1] + (q[1] - p[1]) * dist / L)


fixed, kept, done = 0, 0, set()
anchors = {(v.GetPosition().x, v.GetPosition().y) for v in b.GetTracks() if isinstance(v, pcbnew.PCB_VIA)}
anchors |= {(p.GetPosition().x, p.GetPosition().y) for p in b.GetPads()}
for _ in range(100):
    segs = tracks()
    ends = defaultdict(list)
    for t in segs:
        ends[(t["net"], t["layer"], t["s"])].append(t)
        ends[(t["net"], t["layer"], t["e"])].append(t)
    applied = False
    for s in segs:
        L = math.dist(s["s"], s["e"]) / NM
        if s["uuid"] in done or L > max(JOG_MAX_MM, 4 * s["w"] / NM):
            continue
        p, q = s["s"], s["e"]
        na = [t for t in ends[(s["net"], s["layer"], p)] if t["uuid"] != s["uuid"]]
        nc = [t for t in ends[(s["net"], s["layer"], q)] if t["uuid"] != s["uuid"]]
        if len(na) != 1 or len(nc) != 1 or p in anchors or q in anchors:
            continue
        a, c = na[0], nc[0]
        P0 = a["e"] if a["s"] == p else a["s"]
        P3 = c["e"] if c["s"] == q else c["s"]
        if adiff(ang(P0, p), ang(q, P3)) > PARALLEL_DEG or adiff(ang(P0, p), ang(p, q)) <= PARALLEL_DEG:
            continue
        done.add(s["uuid"])
        obs = obstacles(s["net"], s["layer"])
        width = min(a["w"], s["w"], c["w"])
        # 45-degree bridge: along-A run must equal the sideways offset h
        la, lc = math.dist(P0, p), math.dist(q, P3)
        ux, uy = (p[0] - P0[0]) / la, (p[1] - P0[1]) / la
        jx, jy = q[0] - p[0], q[1] - p[1]
        h, along = abs(jx * uy - jy * ux), jx * ux + jy * uy
        need = h - along                       # da + dc
        cands = []
        if need >= 0:
            for f in SPLITS:
                da, dc = need * f, need * (1 - f)
                if da <= la + 1 and dc <= lc + 1:
                    cands.append((toward(p, P0, da), toward(q, P3, dc)))
        for Pa, Pc in cands:
            bang = adiff(ang(P0, p), ang(Pa, Pc))
            if abs(bang - 45) > 0.5:          # must be exactly 45 degrees to the run
                continue
            if fits(Pa, Pc, width, s["net"], s["layer"], obs):
                ta, ts, tc = by_uuid(a["uuid"]), by_uuid(s["uuid"]), by_uuid(c["uuid"])
                # shorten A and C to the bridge ends (or drop them if fully consumed)
                for t, near, pt in ((ta, p, Pa), (tc, q, Pc)):
                    if (t.GetStart().x, t.GetStart().y) == near:
                        t.SetStart(V(*pt))
                    else:
                        t.SetEnd(V(*pt))
                    if t.GetLength() == 0:
                        b.Delete(t)
                b.Delete(ts)
                bridge = pcbnew.PCB_TRACK(b)
                bridge.SetStart(V(*Pa))
                bridge.SetEnd(V(*Pc))
                bridge.SetWidth(width)
                bridge.SetLayer(s["layer"])
                bridge.SetNetCode(s["net"])
                b.Add(bridge)
                fixed += 1
                applied = True
                break
        else:
            kept += 1
        if applied:
            break  # snapshot is stale: take a new one
    if not applied:
        break

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(board_path, b)
print(json.dumps({"straightened": fixed, "kept": kept, "seconds": round(time.time() - T0, 1)}))
