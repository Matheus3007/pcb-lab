"""Routing quality metrics from build/reports/board.json (pure Python, no KiCad).

A *jog* is a short segment whose two neighbours on the same net and layer run parallel to
each other: the trace steps sideways and continues in the same direction. Jogs are autorouter
artifacts that add length and bends for nothing (noise, impedance discontinuities, ugly).
"""
from __future__ import annotations

import math
from collections import defaultdict

PARALLEL_DEG = 5.0      # neighbours count as parallel within this angle
JOG_MAX_MM = 1.5        # a sideways step shorter than this (or 4x track width) is a jog


def _key(p):
    return (round(p[0], 3), round(p[1], 3))


def _angle(seg, from_pt):
    """Direction of seg leaving from_pt, in degrees."""
    a, b = (seg["start"], seg["end"]) if _key(seg["start"]) == from_pt else (seg["end"], seg["start"])
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def analyze(dump: dict) -> dict:
    # kinks touching a pad or via are pad/via entries, not jogs (matches kijobs/straighten.py)
    anchors = {_key(p["at"]) for f in dump["footprints"] for p in f["pads"]} | {_key(v["at"]) for v in dump["vias"]}
    by_layer = defaultdict(list)
    for t in dump["tracks"]:
        if t["length"] > 0:
            by_layer[(t["net"], t["layer"])].append(t)
    jogs, bends = [], defaultdict(int)
    for (net, layer), segs in by_layer.items():
        ends = defaultdict(list)
        for i, s in enumerate(segs):
            ends[_key(s["start"])].append(i)
            ends[_key(s["end"])].append(i)
        for i, s in enumerate(segs):
            p, q = _key(s["start"]), _key(s["end"])
            # bends: count each 2-segment joint once (at the lower index)
            for pt in (p, q):
                others = [j for j in ends[pt] if j != i]
                if len(others) == 1 and others[0] > i:
                    turn = 180 - _diff(_angle(s, pt), _angle(segs[others[0]], pt))
                    if turn > 1:
                        bends[net] += 1
            if s["length"] > max(JOG_MAX_MM, 4 * s["width"]):
                continue
            np_, nq = [j for j in ends[p] if j != i], [j for j in ends[q] if j != i]
            if len(np_) != 1 or len(nq) != 1 or p in anchors or q in anchors:
                continue
            a, c = segs[np_[0]], segs[nq[0]]
            # direction of travel: into s via a, out of s via c
            dir_in = (_angle(a, p) + 180) % 360
            dir_out = _angle(c, q)
            dir_s = _angle(s, p)
            if _diff(dir_in, dir_out) <= PARALLEL_DEG and _diff(dir_in, dir_s) > PARALLEL_DEG:
                jogs.append({"net": net, "layer": layer, "at": s["start"], "length": s["length"]})
    return {"jogs": jogs, "bends": dict(bends), "bend_total": sum(bends.values())}


def score(dump: dict) -> float:
    """Lower is better. Balanced so neither jogs nor detours can win alone:
    a jog ~ 20 mm of extra copper, a via ~ 3 mm, a bend ~ 1 mm."""
    q = analyze(dump)
    t = dump["totals"]
    return 20 * len(q["jogs"]) + 3 * t["vias"] + 1 * q["bend_total"] + 1 * t["track_length"]
