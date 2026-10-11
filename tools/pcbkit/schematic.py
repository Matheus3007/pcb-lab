"""Generated KiCad schematic: a review view of circuit.py, never a second source of truth.

Split of ownership (this is what makes human edits safe):
- **Connectivity** (parts, nets, NC pins) comes only from circuit.py. Every pin gets a net label
  (or a no-connect flag), regenerated on every build.
- **Layout** (symbol positions/rotation/mirror, field positions, extra wires, labels, junctions and
  notes) lives in boards/<name>/schematic.yaml. It is filled by auto-layout and by *harvesting*:
  move things in KiCad's schematic editor (`make sch-open`), save, and the next build copies the
  layout into schematic.yaml. Anything electrical added in KiCad is validated against circuit.py:
  a wire joining two different nets, or a label naming the wrong net, is dropped and reported.

Also produced: a per-part pin table (symbol pin name vs parts.yaml name, electrical type, net),
the symbol-vs-parts.yaml pin-name cross-check, KiCad ERC, and an SVG/PNG render.
Pure Python except the kicad-cli calls (ERC, SVG export).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import uuid
from pathlib import Path

import yaml

from . import sexpr as S
from .sexpr import Q

SYMDIRS = [Path(__file__).resolve().parents[2] / "lib" / "symbols",
           Path(os.environ.get("KICAD_SYMBOL_DIR", "/mnt/c/Program Files/KiCad/10.0/share/kicad/symbols"))]
LIBNICK = "pcbkit"
G = 1.27                       # schematic grid (50 mil)
CHAR_W = 1.0                   # estimated text advance per character at 1.27 mm font
PAGES = [("A4", 297, 210), ("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594)]
MARGIN = 20.32
PASSIVE_SYMBOLS = {"R": "Device:R", "C": "Device:C", "LED": "Device:LED"}

# Pin names that mean the same thing (datasheets disagree on spelling, not on function).
SYNONYMS = [{"GND", "VSS", "0V"}, {"VIN", "VI", "IN"}, {"VOUT", "VO", "OUT"}, {"VDD", "VCC"},
            {"SHIELD", "SH", "SHLD"}, {"EN", "CE"}]


class SchematicError(Exception):
    pass


def _snap(v: float, g: float = G) -> float:
    return round(round(v / g) * g, 4)


def _uuid(*key) -> Q:
    return Q(str(uuid.uuid5(uuid.NAMESPACE_URL, "pcbkit/" + "/".join(map(str, key)))))


def _font(size=1.27, hide=False, justify=None):
    e = ["effects", ["font", ["size", size, size]]]
    if justify:
        e.append(["justify", *justify])
    if hide:
        e.append(["hide", "yes"])
    return e


# ---------------------------------------------------------------------------- symbol library

class SymbolLib:
    """Loads symbols from lib/symbols/*.kicad_sym (ours, searched first) and KiCad's stock libraries,
    resolving `extends` so every symbol is self-contained."""

    def __init__(self):
        self._libs: dict[str, dict] = {}

    def _lib(self, nick: str) -> dict:
        if nick not in self._libs:
            for d in SYMDIRS:
                f = d / f"{nick}.kicad_sym"
                if f.exists():
                    tree = S.parse(f.read_text(encoding="utf-8"))[0]
                    self._libs[nick] = {c[1]: c for c in S.find_all(tree, "symbol")}
                    break
            else:
                raise SchematicError(f"symbol library {nick!r} not found in {[str(d) for d in SYMDIRS]}")
        return self._libs[nick]

    def get(self, lib_id: str) -> list:
        """Flattened copy of lib:name, named `name` (children renamed name_U_S)."""
        nick, name = lib_id.split(":", 1)
        lib = self._lib(nick)
        if name not in lib:
            raise SchematicError(f"symbol {lib_id} not found")
        sym = copy.deepcopy(lib[name])
        base = S.find(sym, "extends")
        if base:
            parent = self.get(f"{nick}:{base[1]}")
            own_props = {p[1]: p for p in S.find_all(sym, "property")}
            flat = [c for c in parent if S.head(c) != "property"]
            props = [own_props.pop(p[1], p) for p in S.find_all(parent, "property")] + list(own_props.values())
            k = next(i for i, c in enumerate(flat) if isinstance(c, list))
            sym = flat[:k] + props + flat[k:]
            sym[1] = Q(name)
        for u in S.find_all(sym, "symbol"):
            m = re.match(r".*_(\d+_\d+)$", u[1])
            u[1] = Q(f"{name}_{m[1]}")
        return sym


def _pins(sym: list) -> list[dict]:
    """Pins of unit 1 / body style 1 (plus the shared unit 0) in library coordinates (Y up)."""
    out = []
    for u in S.find_all(sym, "symbol"):
        unit, style = map(int, re.match(r".*_(\d+)_(\d+)$", u[1]).groups())
        if unit > 1:
            raise SchematicError(f"{sym[1]}: multi-unit symbols are not supported yet")
        if style > 1:
            continue
        for p in S.find_all(u, "pin"):
            at = S.find(p, "at")
            out.append({"number": str(S.find(p, "number")[1]), "name": str(S.find(p, "name")[1]),
                        "type": p[1], "x": float(at[1]), "y": float(at[2]), "angle": float(at[3]),
                        "length": float(S.find(p, "length")[1]), "hidden": bool(S.find(p, "hide"))})
    return out


def _body_points(sym: list) -> list[tuple[float, float]]:
    pts = []
    for u in S.find_all(sym, "symbol"):
        for g in u:
            h = S.head(g)
            if h == "rectangle":
                pts += [tuple(map(float, S.find(g, k)[1:3])) for k in ("start", "end")]
            elif h in ("polyline", "bezier"):
                pts += [(float(xy[1]), float(xy[2])) for xy in S.find_all(S.find(g, "pts"), "xy")]
            elif h == "circle":
                cx, cy = map(float, S.find(g, "center")[1:3])
                r = float(S.find(g, "radius")[1])
                pts += [(cx - r, cy - r), (cx + r, cy + r)]
            elif h == "arc":
                pts += [tuple(map(float, S.find(g, k)[1:3])) for k in ("start", "mid", "end")]
            elif h == "pin":
                at = S.find(g, "at")
                x, y, a, ln = float(at[1]), float(at[2]), math.radians(float(at[3])), float(S.find(g, "length")[1])
                pts += [(x, y), (x + ln * math.cos(a), y + ln * math.sin(a))]
    return pts or [(-1.27, -1.27), (1.27, 1.27)]


# ---------------------------------------------------------------------------- placement maths

class Placed:
    """A symbol instance: library coords (Y up) -> schematic coords (Y down)."""

    def __init__(self, x, y, rot=0, mirror=None):
        self.x, self.y, self.rot, self.mirror = x, y, int(rot) % 360, mirror

    def pt(self, lx, ly):
        r = math.radians(self.rot)
        vx = lx * math.cos(r) - ly * math.sin(r)
        vy = lx * math.sin(r) + ly * math.cos(r)
        if self.mirror == "y":
            vx = -vx
        elif self.mirror == "x":
            vy = -vy
        return (round(self.x + vx, 4), round(self.y - vy, 4))

    def direction(self, lib_angle):
        """Screen direction (deg, CCW, 0 = +x) of a library direction."""
        d = (lib_angle + self.rot) % 360
        if self.mirror == "y":
            d = (180 - d) % 360
        elif self.mirror == "x":
            d = (-d) % 360
        return round(d) % 360


def _label_len(text: str) -> float:
    return len(text) * CHAR_W + 3.0


def _glabel(net, pt, d, u):
    """Global label: its net name is exactly `net` (local labels become "/net" on the board side)."""
    just = ["left"] if d in (0, 90) else ["right"]
    return ["global_label", Q(net), ["shape", "passive"], ["at", *pt, d], ["fields_autoplaced", "yes"],
            _font(justify=just), ["uuid", u],
            ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", *pt, 0], _font(hide=True)]]


def _bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]


# ---------------------------------------------------------------------------- the generator

class Generator:
    def __init__(self, board: str, netlist: dict, layout: dict, lib: SymbolLib | None = None):
        self.board, self.net, self.layout = board, netlist, layout or {}
        self.lib = lib or SymbolLib()
        self.findings: list[dict] = []
        self.parts = []                     # dicts: part, lib_id, sym, pins, pin_net
        self.auto_uuids: list[str] = []
        self.pin_table: dict[str, list[dict]] = {}

    def f(self, check, severity, msg):
        self.findings.append({"check": f"schematic/{check}", "severity": severity, "msg": msg})

    # -- resolve symbols, cross-check pin names ------------------------------
    def resolve(self):
        pad_net = {}
        nc = set(self.net["no_connect"])
        for p in self.net["parts"]:
            pin_of_pad = {pad: name for name, pads in p["pins"].items() for pad in pads}
            for pad, net in p["pad_nets"].items():
                pad_net[(p["ref"], pad)] = net
            meta = p.get("meta", {})
            lib_id = meta.get("symbol") or PASSIVE_SYMBOLS.get(meta.get("kind"))
            if not lib_id:
                raise SchematicError(f"{p['ref']}: no `symbol:` in lib/parts.yaml for {meta.get('lib_key')}")
            sym = self.lib.get(lib_id)
            pins = _pins(sym)
            aliases = {k: str(v) for k, v in (meta.get("symbol_aliases") or {}).items()}
            rows = []
            sym_numbers = {sp["number"] for sp in pins}
            for sp in pins:
                ours = pin_of_pad.get(sp["number"])
                net = pad_net.get((p["ref"], sp["number"]))
                if ours is None:
                    self.f("pin_unmapped", "error", f"{p['ref']} ({lib_id}): symbol pin {sp['number']} "
                                                    f"'{sp['name']}' has no pad in parts.yaml `pins`")
                elif not _names_match(ours, sp["name"], aliases):
                    self.f("pin_name", "error",
                           f"{p['ref']} pad {sp['number']}: parts.yaml says '{ours}', KiCad symbol {lib_id} says "
                           f"'{sp['name']}'. Check the datasheet; if only the spelling differs, add "
                           f"`symbol_aliases: {{{ours}: \"{sp['name']}\"}}` to the part")
                status = net or (f"NC" if f"{p['ref']}.{ours}" in nc else "—")
                rows.append({"pad": sp["number"], "symbol_name": sp["name"], "name": ours, "type": sp["type"],
                             "net": status})
            for pad in pin_of_pad:
                if pad not in sym_numbers:
                    self.f("pin_unmapped", "error", f"{p['ref']}: pad {pad} ({pin_of_pad[pad]}) is not a pin of "
                                                    f"symbol {lib_id}")
            self.pin_table[p["ref"]] = sorted(rows, key=lambda r: _natural(r["pad"]))
            self.parts.append({"part": p, "lib_id": lib_id, "sym": sym, "pins": pins,
                               "net_of": lambda num, ref=p["ref"]: pad_net.get((ref, num)),
                               "nc_of": lambda num, ref=p["ref"], m=pin_of_pad: f"{ref}.{m.get(num)}" in nc})
        if any(f["severity"] == "error" for f in self.findings):
            self.f("summary", "info", "pin cross-check found mismatches (see above)")
        else:
            self.f("pins_match", "ok", f"all {sum(len(v) for v in self.pin_table.values())} symbol pins match parts.yaml")

    # -- layout ----------------------------------------------------------------
    def _extent(self, item, pl: Placed):
        """Bounding box of a placed symbol, including its labels."""
        pts = [pl.pt(*xy) for xy in _body_points(item["sym"])]
        for sp in item["pins"]:
            net = item["net_of"](sp["number"])
            tip = pl.pt(sp["x"], sp["y"])
            if net:
                d = math.radians(pl.direction(sp["angle"] + 180))
                L = _label_len(net)
                pts.append((tip[0] + L * math.cos(d), tip[1] - L * math.sin(d)))
                pts.append((tip[0] - 1.5 * math.sin(d), tip[1] - 1.5 * math.cos(d)))
        for key in ("Reference", "Value"):
            fx, fy, _ = self._field_pos(item, pl, key)
            w = len(self._field_text(item, key)) * CHAR_W / 2
            pts += [(fx - w, fy - 1), (fx + w, fy + 1)]
        return _bbox(pts)

    def _field_text(self, item, key):
        return item["part"]["ref"] if key == "Reference" else item["part"]["value"]

    def _field_pos(self, item, pl: Placed, key):
        """Default field spot: right of the body if no pin points right, else above, else below."""
        lay = self.layout.get("symbols", {}).get(item["part"]["ref"], {}).get("fields", {}).get(key)
        if lay:
            return pl.x + lay[0], pl.y + lay[1], lay[2] if len(lay) > 2 else 0
        body = _bbox([pl.pt(*xy) for xy in _body_points(item["sym"])])
        dirs = {pl.direction(sp["angle"] + 180) for sp in item["pins"]}
        i = 0 if key == "Reference" else 1
        if 0 not in dirs:
            w = max(len(self._field_text(item, k)) for k in ("Reference", "Value")) * CHAR_W / 2
            cy = (body[1] + body[3]) / 2
            return body[2] + 1.27 + w, cy - 1.27 + 2.54 * i, 0
        if 90 not in dirs:
            return (body[0] + body[2]) / 2, body[1] - 3.81 + 2.54 * i, 0
        return (body[0] + body[2]) / 2, body[3] + 2.54 + 2.54 * i, 0

    def place(self):
        """Positions: schematic.yaml first, auto-layout for the rest (new parts go below)."""
        lay = self.layout.get("symbols", {})
        blocks: dict[str, list] = {}
        for it in self.parts:
            blocks.setdefault(it["part"].get("block") or "main", []).append(it)
        if self.net.get("power_flags"):
            blocks.setdefault("ERC power flags", [])
        placed_boxes = []
        for it in self.parts:
            s = lay.get(it["part"]["ref"])
            if s:
                it["pl"] = Placed(s["at"][0], s["at"][1], s.get("rot", 0), s.get("mirror"))
                placed_boxes.append(self._extent(it, it["pl"]))
        # power flags are pseudo-parts
        self.flags = []
        for net in self.net.get("power_flags", []):
            it = {"part": {"ref": f"#FLG_{net}", "value": "PWR_FLAG", "block": "ERC power flags", "pins": {"1": ["1"]}},
                  "lib_id": "power:PWR_FLAG", "sym": self.lib.get("power:PWR_FLAG"), "flag_net": net}
            it["pins"] = _pins(it["sym"])
            it["net_of"] = lambda num, n=net: n
            it["nc_of"] = lambda num: False
            s = lay.get(f"PWR_FLAG:{net}")
            if s:
                it["pl"] = Placed(s["at"][0], s["at"][1], s.get("rot", 0), s.get("mirror"))
                placed_boxes.append(self._extent(it, it["pl"]))
            self.flags.append(it)
            blocks["ERC power flags"].append(it)
        y0 = (max(b[3] for b in placed_boxes) + 10.16) if placed_boxes else MARGIN + 7.62
        x, y, row_h, max_w = MARGIN + 5.08, y0, 0.0, 250.0
        for name, items in blocks.items():
            todo = [it for it in items if "pl" not in it]
            if not todo:
                continue
            # lay out the block's parts in rows, then place the block as one unit
            bx, by, brow, bw, local = 0.0, 0.0, 0.0, 0.0, []
            for it in todo:
                probe = Placed(0, 0, self._default_rot(it))
                e = self._extent(it, probe)
                w, h = e[2] - e[0], e[3] - e[1]
                if bx and bx + w > 110:
                    bx, by, brow = 0.0, by + brow + 5.08, 0.0
                local.append((it, bx - e[0], by - e[1], probe.rot))
                bx += w + 5.08
                brow = max(brow, h)
                bw = max(bw, bx)
            bh = by + brow
            if x > MARGIN + 5.08 and x + bw > max_w + MARGIN:
                x, y, row_h = MARGIN + 5.08, y + row_h + 15.24, 0.0
            for it, dx, dy, rot in local:
                it["pl"] = Placed(_snap(x + dx, 2.54), _snap(y + dy, 2.54), rot)
            x += bw + 12.7
            row_h = max(row_h, bh)

    @staticmethod
    def _default_rot(it):
        return 0

    # -- emit ------------------------------------------------------------------
    def build(self) -> tuple[str, dict]:
        self.resolve()
        self.place()
        items = self.parts + self.flags
        root = _uuid(self.board, "root")
        lib_symbols = ["lib_symbols"]
        seen = set()
        body, auto = [], []
        pin_points: dict[tuple, list] = {}       # screen point -> [(ref, number, net, nc)]
        for it in items:
            pl = it["pl"]
            for sp in it["pins"]:
                pin_points.setdefault(pl.pt(sp["x"], sp["y"]), []).append(
                    (it["part"]["ref"], sp, it["net_of"](sp["number"]), it["nc_of"](sp["number"]), pl))
        user, wired = self._user_items(pin_points)
        for it in sorted(items, key=lambda i: i["part"]["ref"]):
            name = it["lib_id"].split(":", 1)[1]
            if it["lib_id"] not in seen:
                seen.add(it["lib_id"])
                ls = copy.deepcopy(it["sym"])
                ls[1] = Q(f"{LIBNICK}:{name}")
                lib_symbols.append(ls)
            body.append(self._symbol(it, root))
        # labels: one per connection point, skipped where user wiring already names/joins the net
        for pt, pins in sorted(pin_points.items()):
            nets = {n for _, _, n, _, _ in pins if n}
            ref, sp, net, nc, pl = pins[0]
            if len(nets) > 1:
                self.f("stacked_pins", "error", f"pins at the same spot on different nets: "
                                                f"{[(r, s['number'], n) for r, s, n, _, _ in pins]}")
                continue
            if not nets:
                if all(p[3] for p in pins):
                    u = _uuid(self.board, "nc", ref, sp["number"])
                    auto.append(["no_connect", ["at", *pt], ["uuid", u]])
                continue
            net = nets.pop()
            if pt in wired:
                continue
            d = pl.direction(sp["angle"] + 180)
            u = _uuid(self.board, "label", ref, sp["number"])
            auto.append(_glabel(net, pt, d, u))
        auto += self._frames(items)
        self.auto_uuids = sorted(str(n[-1][1]) for n in auto)
        w, h = self._page(items)
        paper = next((p for p in PAGES if p[1] >= w and p[2] >= h), PAGES[-1])
        title = ["title_block", ["title", Q(self.board)],
                 ["comment", 1, Q("Generated from circuit.py: connectivity is Python-owned; layout edits are kept (schematic.yaml)")]]
        doc = ["kicad_sch", ["version", 20250114], ["generator", Q("pcbkit")], ["generator_version", Q("10.0")],
               ["uuid", root], ["paper", Q(paper[0])], title, lib_symbols, *auto, *user, *body,
               ["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
        symlib = ["kicad_symbol_lib", ["version", 20251024], ["generator", Q("pcbkit")], ["generator_version", Q("10.0")],
                  *[[ls[0], Q(ls[1].split(":", 1)[1]), *ls[2:]] for ls in lib_symbols[1:]]]
        return S.dump(doc) + "\n", {"symlib": S.dump(symlib) + "\n"}

    def _symbol(self, it, root):
        p, pl = it["part"], it["pl"]
        ref = p["ref"]
        is_flag = "flag_net" in it
        node = ["symbol", ["lib_id", Q(f"{LIBNICK}:{it['lib_id'].split(':', 1)[1]}")], ["at", pl.x, pl.y, pl.rot]]
        if pl.mirror:
            node.append(["mirror", pl.mirror])
        dnp = bool(p.get("dnp"))
        node += [["unit", 1], ["exclude_from_sim", "no"], ["in_bom", "no" if dnp or is_flag else "yes"],
                 ["on_board", "no" if is_flag else "yes"], ["dnp", "yes" if dnp else "no"],
                 ["uuid", _uuid(self.board, "sym", ref)]]
        fa = 90 if pl.rot in (90, 270) else 0
        shown_ref = "#FLG0" + str(self.flags.index(it) + 1) if is_flag else ref
        fields = [("Reference", shown_ref, is_flag), ("Value", p["value"], False)]
        for key, text, hide in fields:
            fx, fy, _ = self._field_pos(it, pl, key)
            node.append(["property", Q(key), Q(text), ["at", _snap(fx, 0.01), _snap(fy, 0.01), fa], _font(hide=hide)])
        extra = [("Footprint", p.get("footprint", "")), ("Datasheet", ""), ("Description", "")]
        if not is_flag:   # same optional fields as the footprints (schematic parity compares them)
            extra += [(k, p[k.lower()]) for k in ("LCSC", "MPN") if p.get(k.lower())]
        else:
            extra += [("pcbkit_key", f"PWR_FLAG:{it['flag_net']}")]
        for key, text in extra:
            node.append(["property", Q(key), Q(text), ["at", pl.x, pl.y, 0], _font(hide=True)])
        for sp in sorted(it["pins"], key=lambda s: _natural(s["number"])):
            node.append(["pin", Q(sp["number"]), ["uuid", _uuid(self.board, "pin", ref, sp["number"])]])
        node.append(["instances", ["project", Q(self.board), ["path", Q(f"/{root}"),
                                                              ["reference", Q(shown_ref)], ["unit", 1]]]])
        return node

    def _frames(self, items):
        boxes: dict[str, list] = {}
        for it in items:
            boxes.setdefault(it["part"].get("block") or "main", []).append(self._extent(it, it["pl"]))
        out = []
        if list(boxes) == ["main"]:
            return out
        for name, bs in boxes.items():
            x0, y0 = min(b[0] for b in bs) - 2.54, min(b[1] for b in bs) - 2.54
            x1, y1 = max(b[2] for b in bs) + 2.54, max(b[3] for b in bs) + 2.54
            out.append(["rectangle", ["start", _snap(x0), _snap(y0)], ["end", _snap(x1), _snap(y1)],
                        ["stroke", ["width", 0], ["type", "dash"], ["color", 132, 132, 132, 1]], ["fill", ["type", "none"]],
                        ["uuid", _uuid(self.board, "frame", name)]])
            out.append(["text", Q(name), ["exclude_from_sim", "no"], ["at", _snap(x0), _snap(y0 - 1.27), 0],
                        _font(size=1.778, justify=["left", "bottom"]), ["uuid", _uuid(self.board, "frametitle", name)]])
        return out

    def _page(self, items):
        bs = [self._extent(it, it["pl"]) for it in items]
        return max(b[2] for b in bs) + MARGIN, max(b[3] for b in bs) + MARGIN + 30

    # -- user-drawn items (wires, labels, junctions, notes), validated -------------
    def _user_items(self, pin_points):
        """Emit schematic.yaml's wires/labels/junctions/texts. Wire groups must stay inside one net."""
        lay = self.layout
        wires = [tuple(map(float, w)) for w in lay.get("wires", [])]
        labels = lay.get("labels", [])
        parent = list(range(len(wires)))

        def root(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def on(seg, pt):
            (x1, y1, x2, y2), (px, py) = seg, pt
            cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
            return abs(cross) < 1e-3 and min(x1, x2) - 1e-3 <= px <= max(x1, x2) + 1e-3 \
                and min(y1, y2) - 1e-3 <= py <= max(y1, y2) + 1e-3

        for i, a in enumerate(wires):
            for j in range(i):
                b = wires[j]
                if any(on(b, p) for p in (a[:2], a[2:])) or any(on(a, p) for p in (b[:2], b[2:])):
                    parent[root(i)] = root(j)
        groups: dict[int, dict] = {}
        for i, w in enumerate(wires):
            g = groups.setdefault(root(i), {"wires": [], "nets": set(), "pins": [], "labels": []})
            g["wires"].append(i)
            for pt, pins in pin_points.items():
                if on(w, pt):
                    g["pins"].append(pt)
                    for ref, sp, net, nc, _ in pins:
                        g["nets"].add(net or f"<NC {ref}.{sp['number']}>")
        for lb in labels:
            pt = tuple(map(float, lb["at"][:2]))
            hit = [k for k, g in groups.items() if any(on(wires[i], pt) for i in g["wires"])]
            if hit:
                groups[hit[0]]["labels"].append(lb)
                groups[hit[0]]["nets"].add(lb["net"])
            elif pt not in pin_points:
                self.f("user_label_dangling", "warning", f"label {lb['net']} at {pt} touches no wire or pin: dropped")
            elif {p[2] for p in pin_points[pt]} != {lb["net"]}:
                self.f("user_label_wrong_net", "error", f"label {lb['net']} at {pt} is on a pin of net "
                                                         f"{[p[2] for p in pin_points[pt]]}: dropped (circuit.py owns nets)")
            else:
                groups.setdefault(-1 - len(groups), {"wires": [], "nets": {lb["net"]}, "pins": [pt], "labels": [lb]})
        out, wired = [], set()
        for k, g in sorted(groups.items()):
            if len(g["nets"]) > 1:
                self.f("user_wire_short", "error", f"hand-drawn wires/labels join different nets {sorted(g['nets'])}: "
                                                   f"dropped (circuit.py owns connectivity)")
                continue
            for i in g["wires"]:
                x1, y1, x2, y2 = wires[i]
                out.append(["wire", ["pts", ["xy", x1, y1], ["xy", x2, y2]], ["stroke", ["width", 0], ["type", "default"]],
                            ["uuid", _uuid(self.board, "wire", x1, y1, x2, y2)]])
            for lb in g["labels"]:
                d = int(lb.get("rot", 0))
                out.append(_glabel(lb["net"], lb["at"][:2], d, _uuid(self.board, "ulabel", lb["net"], *lb["at"][:2])))
            # pins on a wired group: one auto label at the first pin unless the user labelled it
            pins = sorted(set(g["pins"]))
            if g["labels"]:
                wired.update(pins)
            elif pins:
                wired.update(pins[1:])
        for jx, jy in lay.get("junctions", []):
            out.append(["junction", ["at", jx, jy], ["diameter", 0], ["color", 0, 0, 0, 0], ["uuid", _uuid(self.board, "junction", jx, jy)]])
        for t in lay.get("texts", []):
            out.append(["text", Q(t["text"]), ["exclude_from_sim", "no"], ["at", *t["at"][:2], t.get("rot", 0)],
                        _font(size=t.get("size", 1.27), justify=["left", "bottom"]),
                        ["uuid", _uuid(self.board, "text", t["text"], *t["at"][:2])]])
        return out, wired


def _norm(n: str) -> str:
    return re.sub(r"[\s_~{}/]", "", n.upper().replace("+", "P").replace("-", "N"))


def _names_match(ours: str, theirs: str, aliases: dict) -> bool:
    if theirs in ("", "~") or re.fullmatch(r"Pin_\d+", theirs) or aliases.get(ours) == theirs:
        return True
    a, b = _norm(ours), _norm(theirs)
    if a == b or re.sub(r"\d+$", "", a) == b:
        return True
    return any(a in s and b in s for s in SYNONYMS)


def _natural(s: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def compare_netlist(knet_text: str, netlist: dict) -> list[dict]:
    """KiCad's netlist of the generated schematic vs circuit.py: same pads on the same named nets."""
    tree = S.parse(knet_text)[0]
    got: dict[str, set] = {}
    for n in S.find_all(S.find(tree, "nets"), "net"):
        name = str(S.find(n, "name")[1]).lstrip("/")
        nodes = {(str(S.find(x, "ref")[1]), str(S.find(x, "pin")[1])) for x in S.find_all(n, "node")}
        nodes = {x for x in nodes if not x[0].startswith("#")}
        if nodes and not name.startswith("unconnected-"):
            got[name] = nodes
    want: dict[str, set] = {}
    for p in netlist["parts"]:
        for pad, net in p["pad_nets"].items():
            want.setdefault(net, set()).add((p["ref"], pad))
    out = []
    for net in sorted(set(got) | set(want)):
        if got.get(net) != want.get(net):
            out.append({"check": "schematic/netlist_mismatch", "severity": "error",
                        "msg": f"net {net}: circuit.py {sorted(want.get(net, []))} vs schematic {sorted(got.get(net, []))}"})
    if not out:
        out.append({"check": "schematic/netlist_match", "severity": "ok",
                    "msg": f"KiCad's netlist of the schematic equals circuit.py ({len(want)} nets)"})
    return out


# ---------------------------------------------------------------------------- harvest

def harvest(sch_text: str, auto_uuids: set[str]) -> dict:
    """Layout from a (possibly human-edited) schematic: symbol placement + field offsets, and every
    wire/label/junction/text that the generator did not create itself."""
    tree = S.parse(sch_text)[0]
    out = {"symbols": {}, "wires": [], "labels": [], "junctions": [], "texts": []}
    for s in S.find_all(tree, "symbol"):
        at = S.find(s, "at")
        x, y, rot = round(float(at[1]), 4), round(float(at[2]), 4), int(float(at[3])) if len(at) > 3 else 0
        key = S.prop(s, "pcbkit_key") or S.prop(s, "Reference")
        if not key:
            continue
        entry = {"at": [x, y], "rot": rot}
        m = S.find(s, "mirror")
        if m:
            entry["mirror"] = str(m[1])
        fields = {}
        for p in S.find_all(s, "property"):
            if p[1] in ("Reference", "Value") and not S.find(S.find(p, "effects") or [], "hide"):
                pa = S.find(p, "at")
                fields[str(p[1])] = [round(float(pa[1]) - x, 4), round(float(pa[2]) - y, 4)]
        entry["fields"] = fields
        out["symbols"][key] = entry
    for n in tree[1:]:
        h = S.head(n)
        u = S.find(n, "uuid") if isinstance(n, list) else None
        if not u or str(u[1]) in auto_uuids:
            continue
        if h == "wire":
            xy = S.find_all(S.find(n, "pts"), "xy")
            out["wires"].append([float(xy[0][1]), float(xy[0][2]), float(xy[1][1]), float(xy[1][2])])
        elif h in ("label", "global_label", "hierarchical_label"):
            at = S.find(n, "at")
            out["labels"].append({"net": str(n[1]), "at": [float(at[1]), float(at[2])], "rot": int(float(at[3]))})
        elif h == "junction":
            at = S.find(n, "at")
            out["junctions"].append([float(at[1]), float(at[2])])
        elif h == "text":
            at = S.find(n, "at")
            size = float(S.find(S.find(S.find(n, "effects"), "font"), "size")[1])
            out["texts"].append({"text": str(n[1]), "at": [float(at[1]), float(at[2])], "rot": int(float(at[3])), "size": size})
    for k in ("wires", "labels", "junctions", "texts"):
        out[k] = sorted(out[k], key=json.dumps)
        if not out[k]:
            del out[k]
    out["symbols"] = dict(sorted(out["symbols"].items()))
    return out


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


LAYOUT_HEADER = """\
# Schematic LAYOUT only (presentation). Connectivity is owned by circuit.py: nets, labels on pins and
# no-connect flags are regenerated every build, and hand-drawn wires/labels that contradict circuit.py
# are dropped and reported. Edit here, or move things in KiCad (`make sch-open BOARD=...`), save, and
# rebuild: the build copies the KiCad layout back into this file. Parts missing here are auto-placed.
"""


def write_layout(path: Path, layout: dict) -> None:
    class D(yaml.SafeDumper):
        pass

    def flow_list(d, v):
        return d.represent_sequence("tag:yaml.org,2002:seq", v, flow_style=all(not isinstance(x, (dict, list)) for x in v))
    D.add_representer(list, flow_list)
    path.write_text(LAYOUT_HEADER + yaml.dump(layout, Dumper=D, sort_keys=False, width=120), encoding="utf-8")
