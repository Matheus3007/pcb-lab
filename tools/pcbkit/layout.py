"""Layout hygiene: geometry checks DRC doesn't do (noise, return paths, stubs). Pure Python + shapely
on build/work/copper.json (kijobs/copper.py) and build/reports/board.json (kijobs/dump.py).

Configured by routing.yaml `layout:` (all keys optional):
  reference_layers: {F.Cu: In1.Cu, ...}   # which layer is each signal layer's return path
  return_path: {ignore: [NET, ...], max_gap_mm: 0.3}   # per net, total length over gaps
  fingers: {max_mm: 3.0, min_width_mm: 0.8}
  loops: [{name, path: [REF.PAD, ...], max_area_mm2, same_layer_return: true, via_max_mm: 1.5}]
  pairs: [{nets: [P, N], max_skew_mm, max_vias}]
  sensitive: [{nets: [...], max_vias: 2}, ...]
"""
from __future__ import annotations

import json
import math

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

# nearest plane for each signal layer. JLC 4-layer stackups put thin prepreg between F/In1 and In2/B
# and the thick core in the middle, so In2's and B's return currents flow in each other, not in In1.
DEFAULT_REFS = {2: {"F.Cu": "B.Cu", "B.Cu": "F.Cu"},
                4: {"F.Cu": "In1.Cu", "In1.Cu": "F.Cu", "In2.Cu": "B.Cu", "B.Cu": "In2.Cu"}}


def _poly(p):
    return Polygon(p[0], p[1:]).buffer(0)


def _union(polys):
    return unary_union([_poly(p) for p in polys]) if polys else Polygon()


def _parts(geom):
    return list(getattr(geom, "geoms", [geom])) if not geom.is_empty else []


class Copper:
    def __init__(self, path):
        d = json.loads(path.read_text())
        self.fill = {l: {n: _union(ps) for n, ps in nets.items()} for l, nets in d["fills"].items()}
        self.item = {l: {n: _union(ps) for n, ps in nets.items()} for l, nets in d["items"].items()}
        self.layers = list(d["fills"])

    def net(self, layer, net, fills=True):
        g = [self.item.get(layer, {}).get(net, Polygon())]
        if fills:
            g.append(self.fill.get(layer, {}).get(net, Polygon()))
        return unary_union(g)


def _f(check, severity, msg):
    return {"check": check, "severity": severity, "msg": msg}


def return_path(cu: Copper, dump: dict, cfg: dict, ground: str) -> list[dict]:
    refs = cfg.get("reference_layers") or DEFAULT_REFS.get(dump["layers"], {})
    rp = cfg.get("return_path", {})
    ignore = set(rp.get("ignore", [])) | {ground}
    max_gap = rp.get("max_gap_mm", 0.3)
    plane = {l: cu.net(l, ground) for l in cu.layers}
    gaps: dict[str, list] = {}
    for t in dump["tracks"]:
        if t["net"] in ignore or t["layer"] not in refs:
            continue
        line = LineString([t["start"], t["end"]])
        if line.length == 0:
            continue
        ref = refs[t["layer"]]
        # a track landing on its own via/THT pad crosses that item's clearance hole in the plane: not a gap
        own = cu.item.get(ref, {}).get(t["net"])
        miss = line.difference(plane[ref] if own is None else unary_union([plane[ref], own.buffer(0.35)]))
        if miss.length > 0.05:
            mid = miss.centroid
            gaps.setdefault(t["net"], []).append((miss.length, t["layer"], refs[t["layer"]], mid.x, mid.y))
    res = []
    for net, g in sorted(gaps.items()):
        total = sum(x[0] for x in g)
        worst = max(g)
        sev = "warning" if total > max_gap else "info"
        res.append(_f("layout/return_path", sev,
                      f"{net}: {total:.2f} mm of track has no {ground} under it on the reference layer "
                      f"(worst {worst[0]:.2f} mm on {worst[1]} over a gap in {worst[2]} at ({worst[3]:.2f}, {worst[4]:.2f})); "
                      f"the return current detours around the gap (loop area, crosstalk)"))
    if not res:
        res.append(_f("layout/return_path", "ok", f"every signal track has unbroken {ground} on its reference layer"))
    return res


def fingers(cu: Copper, dump: dict, cfg: dict, ground: str) -> list[dict]:
    """Dead-end narrow tongues of a pour (stubs that resonate/radiate) with no via or pad on them."""
    fc = cfg.get("fingers", {})
    max_len, r = fc.get("max_mm", 3.0), fc.get("min_width_mm", 0.8) / 2
    res = []
    for layer in cu.layers:
        fill = cu.fill[layer].get(ground)
        if fill is None or fill.is_empty:
            continue
        anchors = cu.item[layer].get(ground, Polygon())
        body = fill.buffer(-r).buffer(r)
        for narrow in _parts(fill.difference(body.buffer(0.01))):
            if narrow.area < 0.05:
                continue
            rect = narrow.minimum_rotated_rectangle
            xs = list(rect.exterior.coords)
            length = max(math.dist(xs[i], xs[i + 1]) for i in range(4))
            touches = len(_parts(narrow.buffer(0.05).intersection(body)))
            if length <= max_len or touches > 1 or narrow.intersects(anchors):
                continue
            c = narrow.centroid
            res.append(_f("layout/finger", "warning",
                          f"{ground} pour on {layer}: {length:.1f} mm dead-end tongue narrower than {2 * r:.1f} mm at "
                          f"({c.x:.2f}, {c.y:.2f}) with no via; stitch its tip or keep it out (zone keepout/min width)"))
    if not res:
        res.append(_f("layout/finger", "ok", f"no unstitched dead-end {ground} tongues longer than {max_len} mm"))
    return res


def _pad(dump, spec):
    ref, num = spec.split(".")
    fp = next(f for f in dump["footprints"] if f["ref"] == ref)
    return next(p for p in fp["pads"] if p["num"] == num), fp


def loops(cu: Copper, dump: dict, cfg: dict) -> list[dict]:
    res = []
    for lp in cfg.get("loops", []):
        pads = [_pad(dump, s) for s in lp["path"]]
        pts = [p["at"] for p, _ in pads]
        area = Polygon(pts).area if len(pts) >= 3 else 0.0
        sev = "ok" if area <= lp["max_area_mm2"] else "warning"
        res.append(_f("layout/loop", sev, f"{lp['name']}: {area:.2f} mm² enclosed by {' → '.join(lp['path'])} "
                                          f"(max {lp['max_area_mm2']} mm²)"))
        if not lp.get("same_layer_return", True):
            continue
        # every hop between pads of the same net must be one piece of copper on the parts' layer:
        # no via/plane detour inside the loop
        for (a, fa), (b2, fb), sa, sb in zip(pads, pads[1:] + pads[:1], lp["path"], lp["path"][1:] + lp["path"][:1]):
            if a["net"] != b2["net"]:
                continue
            layer = "F.Cu" if fa["side"] == "top" else "B.Cu"
            cop = cu.net(layer, a["net"])
            pa, pb = Point(a["at"]), Point(b2["at"])
            joined = any(g.distance(pa) < 0.05 and g.distance(pb) < 0.05 for g in _parts(cop))
            if joined:
                continue
            # else each pad needs its own via to the plane right next to it (shortest vertical hop)
            vmax = lp.get("via_max_mm", 1.5)
            near = [min((math.dist(v["at"], q["at"]) for v in dump["vias"] if v["net"] == a["net"]), default=99)
                    for q in (a, b2)]
            sev = "ok" if max(near) <= vmax else "warning"
            res.append(_f("layout/loop", sev,
                          f"{lp['name']}: {sa} and {sb} ({a['net']}) are not joined by copper on {layer}; nearest "
                          f"{a['net']} vias {near[0]:.2f} / {near[1]:.2f} mm from them (max {vmax} mm, so the "
                          f"return drops straight into the plane)"))
    return res


def pairs(dump: dict, cfg: dict) -> list[dict]:
    res = []
    for pr in cfg.get("pairs", []):
        p, n = pr["nets"]
        info = {x: dump["nets"].get(x, {}) for x in (p, n)}
        lens = {x: info[x].get("track_length", 0.0) for x in (p, n)}
        layers = {x: sorted({t["layer"] for t in dump["tracks"] if t["net"] == x}) for x in (p, n)}
        vias = {x: info[x].get("vias", 0) for x in (p, n)}
        skew = abs(lens[p] - lens[n])
        res.append(_f("layout/pair", "ok" if skew <= pr.get("max_skew_mm", 1.0) else "warning",
                      f"{p}/{n}: lengths {lens[p]:.2f}/{lens[n]:.2f} mm, skew {skew:.2f} mm (max {pr.get('max_skew_mm', 1.0)})"))
        if layers[p] != layers[n] or vias[p] != vias[n]:
            res.append(_f("layout/pair", "warning", f"{p}/{n}: not routed alike (layers {layers[p]} vs {layers[n]}, "
                                                    f"vias {vias[p]} vs {vias[n]})"))
        if max(vias.values()) > pr.get("max_vias", 2):
            res.append(_f("layout/pair", "warning", f"{p}/{n}: {max(vias.values())} vias per net (max {pr.get('max_vias', 2)})"))
    return res


def sensitive(dump: dict, cfg: dict) -> list[dict]:
    groups = cfg.get("sensitive", [])
    res = []
    for s in [groups] if isinstance(groups, dict) else groups:
        for net in s.get("nets", []):
            v = dump["nets"].get(net, {}).get("vias", 0)
            if v > s.get("max_vias", 2):
                res.append(_f("layout/vias", "warning", f"{net}: {v} vias (sensitive net, max {s.get('max_vias', 2)}); "
                                                        f"each via is a reference-plane change for its return current"))
    return res


def check(work, dump: dict, cfg: dict, ground: str = "GND") -> list[dict]:
    path = work / "copper.json"
    if not path.exists() or not dump["tracks"]:
        return []
    cu = Copper(path)
    return (return_path(cu, dump, cfg, ground) + fingers(cu, dump, cfg, ground) + loops(cu, dump, cfg)
            + pairs(dump, cfg) + sensitive(dump, cfg))
