"""Stage 5: all automated checks -> build/reports/checks.json + summary.md.

Sources: circuit validation/assertions, KiCad DRC (JSON), placement rules, assembly-tier
rules, JLC part data, net-class current capacity, 3D model presence. Accepted findings are
listed in boards/<name>/waivers.yaml ({check, match, reason}); everything else at
severity "error" fails the stage.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from . import jlc
from .pipeline import ROOT, Board, kicad_cli, yload

KICAD_3D = Path("/mnt/c/Program Files/KiCad/10.0/share/kicad/3dmodels")


def _f(check, severity, msg, **extra):
    return {"check": check, "severity": severity, "msg": msg, **extra}


# --------------------------------------------------------------------------- DRC
def drc(b: Board) -> list[dict]:
    raw = b.work / "drc.json"
    # --schematic-parity: the board must match the generated schematic (same dir + name)
    kicad_cli("pcb", "drc", "--format", "json", "--severity-all", "--units", "mm", "--schematic-parity",
              "-o", raw, b.pcb, ok_codes=(0, 5))
    d = json.loads(raw.read_text())
    # keep the committed report stable across identical builds: no date, no per-build UUIDs
    d.pop("date", None)
    for key in ("violations", "unconnected_items", "schematic_parity"):
        for v in d.get(key, []):
            for it in v.get("items", []):
                it.pop("uuid", None)
        d.get(key, []).sort(key=lambda v: json.dumps(v, sort_keys=True))
    (b.reports / "drc.json").write_text(json.dumps(d, indent=1) + "\n")
    res = []
    for v in d.get("violations", []):
        items = "; ".join(i["description"] for i in v["items"])
        res.append(_f(f"drc/{v['type']}", v["severity"], f"{v['description']}: {items}"))
    for v in d.get("unconnected_items", []):
        items = "; ".join(i["description"] for i in v["items"])
        res.append(_f("drc/unconnected", "error", f"unconnected: {items}"))
    # KiCad names NC pins "unconnected-(...)"; our board leaves NC pads net-less, which means the same
    d["schematic_parity"] = [v for v in d.get("schematic_parity", [])
                             if not ("unconnected-(" in v["description"] and "missing net" in v["description"])]
    for v in d.get("schematic_parity", []):
        items = "; ".join(i["description"] for i in v["items"])
        res.append(_f(f"parity/{v['type']}", "error", f"{v['description']}: {items}"))
    if not d.get("schematic_parity"):
        res.append(_f("parity/ok", "ok", "board matches the schematic (KiCad schematic parity)"))
    return res


# --------------------------------------------------------------------------- schematic
def schematic(b: Board) -> list[dict]:
    """Pin-name cross-check, KiCad-netlist equality, hand-edit validation, and ERC."""
    sj = b.reports / "schematic.json"
    if not sj.exists():
        return [_f("schematic/missing", "error", "no schematic report: run make sch / make build")]
    res = [_f(f["check"], f["severity"], f["msg"]) for f in json.loads(sj.read_text())["findings"]]
    erc = json.loads((b.reports / "erc.json").read_text())
    for v in erc["violations"]:
        items = "; ".join(i["description"] for i in v["items"])
        res.append(_f(f"erc/{v['type']}", v["severity"], f"{v['description']}: {items}"))
    if not erc["violations"]:
        res.append(_f("erc/ok", "ok", "KiCad ERC: no violations"))
    return res


# --------------------------------------------------------------------------- placement
def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def placement(b: Board, dump: dict) -> list[dict]:
    fps = {f["ref"]: f for f in dump["footprints"]}
    bx0, by0, bx1, by1 = dump["board_bbox"]
    res = []
    for r in yload(b.dir / "placement.yaml").get("rules", []):
        ref = fps.get(r["ref"])
        if ref is None:
            res.append(_f("placement/rule", "error", f"rule refers to missing part {r['ref']}"))
            continue
        if r["rule"] == "near":
            tgt = fps[r["to"]]
            tpads = [p for p in tgt["pads"] if p["num"] == str(r["pin_pad"])]
            d = min(_dist(p["at"], q["at"]) for p in ref["pads"] for q in tpads)
            sev = "ok" if d <= r["max_dist"] else "error"
            res.append(_f("placement/near", sev,
                          f"{r['ref']} -> {r['to']} pad {r['pin_pad']}: {d:.2f} mm (max {r['max_dist']}) — {r.get('why', '')}"))
        elif r["rule"] == "on_edge":
            x0, y0, x1, y1 = ref["courtyard"]
            gap = {"top": y0 - by0, "bottom": by1 - y1, "left": x0 - bx0, "right": bx1 - x1}[r["edge"]]
            sev = "ok" if gap <= r.get("max_gap", 0.6) else "error"
            res.append(_f("placement/on_edge", sev, f"{r['ref']} courtyard {gap:+.2f} mm from {r['edge']} edge — {r.get('why', '')}"))
    return res


# --------------------------------------------------------------------------- assembly
def assembly(b: Board, dump: dict, netlist: dict) -> list[dict]:
    rules = b.assembly_rules()
    res = []
    size = dump["size_mm"]
    mn = rules["min_board_mm"]
    if size[0] < mn[0] or size[1] < mn[1]:
        res.append(_f("assembly/board_size", "error",
                      f"board {size[0]}x{size[1]} mm below {b.tier} PCBA minimum {mn[0]}x{mn[1]} mm (panelize)"))
    order = ["01005", "0201", "0402", "0603", "0805", "1206"]
    min_pkg = order.index(rules["min_package"])
    for f in dump["footprints"]:
        if f["dnp"]:
            continue
        if f["side"] not in rules["sides"]:
            res.append(_f("assembly/side", "error", f"{f['ref']} on {f['side']} but {b.tier} PCBA assembles {rules['sides']}"))
        m = re.search(r"_(01005|0201|0402|0603|0805|1206)_", f["footprint"])
        if m and order.index(m.group(1)) < min_pkg:
            res.append(_f("assembly/package", "error", f"{f['ref']} {m.group(1)} smaller than {b.tier} minimum {rules['min_package']}"))
    return res


# --------------------------------------------------------------------------- parts
def parts(b: Board, netlist: dict) -> tuple[list[dict], list[dict]]:
    res, bom = [], {}
    for p in netlist["parts"]:
        if p["dnp"]:
            continue
        if p["meta"].get("lib_key") and not (p["meta"].get("pinout_source") and p["meta"].get("pinout_verified")):
            res.append(_f("parts/pinout_evidence", "error", f"{p['ref']} ({p['meta']['lib_key']}) has no recorded pinout verification"))
        try:
            info = jlc.lookup(p["lcsc"])
        except Exception as e:  # noqa: BLE001
            res.append(_f("parts/jlc_lookup", "error", f"{p['ref']} {p['lcsc']}: {e}"))
            continue
        if info["tier"] == "extended" and not p["meta"].get("extended_reason"):
            res.append(_f("parts/extended", "warning",
                          f"{p['ref']} {p['lcsc']} is a plain Extended part (setup fee). Prefer Basic or Preferred "
                          f"Extended; if none fits, add `extended_reason:` to its parts.yaml entry"))
        row = bom.setdefault(p["lcsc"], {**info, "refs": [], "value": p["value"], "footprint": p["footprint"]})
        row["refs"].append(p["ref"])
    qty = b.cfg.get("quantity", 5)
    for row in bom.values():
        need = qty * len(row["refs"])
        if (row["stock"] or 0) < need * 3:
            res.append(_f("parts/stock", "error" if (row["stock"] or 0) < need else "warning",
                          f"{row['lcsc']} stock {row['stock']} vs need {need} (as of {row['fetched']})"))
    ext = [r for r in bom.values() if r["tier"] == "extended"]
    res.append(_f("parts/tiers", "info",
                  f"{len(bom)} unique parts: " + ", ".join(f"{t} {sum(r['tier'] == t for r in bom.values())}"
                                                           for t in ("basic", "preferred", "extended"))
                  + (f" (extended: {', '.join(r['lcsc'] + ' ' + (r['mpn'] or '') for r in ext)})" if ext else "")))
    return res, sorted(bom.values(), key=lambda r: r["refs"][0])


# --------------------------------------------------------------------------- current capacity
def ipc2221_width_mm(current_a: float, dt_c: float = 10.0, oz: float = 1.0, external: bool = True) -> float:
    k = 0.048 if external else 0.024
    area_mil2 = (current_a / (k * dt_c ** 0.44)) ** (1 / 0.725)
    return area_mil2 / (1.378 * oz) * 0.0254


def current(b: Board, dump: dict, netlist: dict) -> list[dict]:
    res = []
    oz = b.cfg.get("copper_oz", 1.0)
    for cname, nc in netlist["net_classes"].items():
        if not nc.get("current_a"):
            continue
        need = ipc2221_width_mm(nc["current_a"], oz=oz)
        for net, info in netlist["nets"].items():
            if info["class"] != cname or net not in dump["nets"]:
                continue
            w = dump["nets"][net]["min_width"]
            if w is None:
                continue
            sev = "ok" if w >= need else "error"
            res.append(_f("current/width", sev, f"{net}: min track {w} mm vs {need:.3f} mm needed for {nc['current_a']} A (IPC-2221, ΔT 10 °C, {oz} oz)"))
    return res


# --------------------------------------------------------------------------- routing quality
def routing(b: Board, dump: dict) -> list[dict]:
    from . import routeq
    q = routeq.analyze(dump)
    res = [_f("routing/jog", "warning",
              f"{j['net']} on {j['layer']}: {j['length']:.2f} mm sideways step at ({j['at'][0]:.2f}, {j['at'][1]:.2f}) "
              f"(board coords, +Y down); straighten it (REROUTE=1, placement, or a scripted track)")
           for j in q["jogs"]]
    res.append(_f("routing/stats", "info", f"{q['bend_total']} bends total; per net: "
                  + ", ".join(f"{n} {c}" for n, c in sorted(q["bends"].items()))))
    return res


# --------------------------------------------------------------------------- 3D models
def models(b: Board) -> list[dict]:
    txt = b.pcb.read_text(encoding="utf-8")
    res = []
    # footprints with no model at all (our own lib/footprints ones start without one)
    for blk in re.split(r"\n\t\(footprint ", txt)[1:]:
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if ref and "(model " not in blk and "(attr " in blk and "exclude_from_bom" not in blk \
                and not ref[1].startswith(("H", "#")):
            res.append(_f("models/missing", "warning", f"{ref[1]}: no 3D model referenced, 3D fit checks blind for this part"))
    for ref, path in re.findall(r'\(property "Reference" "([^"]+)".*?\(model "([^"]+)"', txt, flags=re.S):
        p = path.replace("${KICAD10_3DMODEL_DIR}", str(KICAD_3D))
        if re.match(r"^[A-Za-z]:\\", p):
            p = "/mnt/" + p[0].lower() + p[2:].replace("\\", "/")
        if not Path(p).exists():
            res.append(_f("models/missing", "warning", f"{ref}: 3D model not found ({path}), 3D fit checks blind for this part"))
    return res


# --------------------------------------------------------------------------- driver
def apply_waivers(b: Board, findings: list[dict]) -> None:
    waivers = yload(b.dir / "waivers.yaml", default=[]) or []
    for f in findings:
        for w in waivers:
            if f["check"].startswith(w["check"]) and w.get("match", "") in f["msg"]:
                f["waived"] = w["reason"]


def check(name: str) -> dict:
    b = Board(name)
    dump = json.loads((b.reports / "board.json").read_text())
    netlist = json.loads((b.work / "netlist.json").read_text())
    circ = json.loads((b.reports / "circuit.json").read_text())
    findings = [_f(f"circuit/{i['check']}", i["severity"], i["msg"]) for i in circ["issues"]]
    findings += [_f("circuit/assertion", "ok" if a["ok"] else "error",
                    f"{a['name']}: {a['value']:.4g} {a['unit']} in [{a['min']:.4g}, {a['max']:.4g}]")
                 for a in circ["assertions"]]
    findings += schematic(b)
    findings += drc(b)
    findings += placement(b, dump)
    findings += assembly(b, dump, netlist)
    pf, bom = parts(b, netlist)
    findings += pf
    findings += current(b, dump, netlist)
    findings += routing(b, dump)
    findings += models(b)
    apply_waivers(b, findings)

    errors = [f for f in findings if f["severity"] == "error" and "waived" not in f]
    warnings = [f for f in findings if f["severity"] == "warning" and "waived" not in f]
    result = {"board": name, "pass": not errors, "errors": len(errors), "warnings": len(warnings),
              "waived": sum("waived" in f for f in findings), "findings": findings, "bom": bom,
              "stats": {"size_mm": dump["size_mm"], **dump["totals"], "parts": len(dump["footprints"])}}
    (b.reports / "checks.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    (b.reports / "summary.md").write_text(summary_md(result), encoding="utf-8")
    return result


def summary_md(r: dict) -> str:
    s = r["stats"]
    lines = [f"# {r['board']} — checks {'PASS' if r['pass'] else 'FAIL'}", "",
             f"{r['errors']} errors · {r['warnings']} warnings · {r['waived']} waived  ",
             f"board {s['size_mm'][0]} × {s['size_mm'][1]} mm · {s['parts']} footprints · "
             f"{s['tracks']} track segments · {s['vias']} vias · {s['track_length']} mm copper", ""]
    groups: dict[str, list] = {}
    for f in r["findings"]:
        groups.setdefault(f["check"].split("/")[0], []).append(f)
    icon = {"error": "✗", "warning": "!", "ok": "✓", "info": "·"}
    # errors/warnings first, collapsed counts for repetitive DRC warnings
    for g, fs in groups.items():
        lines.append(f"## {g}")
        seen: dict[str, int] = {}
        for f in sorted(fs, key=lambda f: ["error", "warning", "info", "ok"].index(f["severity"])):
            key = f["check"] + f["severity"] + ("w" if "waived" in f else "")
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > 5:
                continue
            tag = f" _(waived: {f['waived']})_" if "waived" in f else ""
            lines.append(f"- {icon[f['severity']]} `{f['check']}` {f['msg']}{tag}")
        for key, n in seen.items():
            if n > 5:
                lines.append(f"- … {n - 5} more `{key}`")
        lines.append("")
    return "\n".join(lines)
