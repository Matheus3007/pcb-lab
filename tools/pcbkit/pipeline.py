"""Pipeline stages, run from WSL. KiCad work is delegated to kijobs/* via toolchain/bin/kipy.

Every stage reads sources from boards/<name>/ and writes to boards/<name>/build/.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLBIN = ROOT / "toolchain" / "bin"
KIJOBS = Path(__file__).resolve().parent / "kijobs"


class StageError(Exception):
    pass


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    cmd = [str(c) for c in cmd]
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0 and not kw.get("check") is False:
        raise StageError(f"command failed ({r.returncode}): {' '.join(cmd)}\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r


def kipy(script: str, *args) -> str:
    return run([TOOLBIN / "kipy", KIJOBS / script, *args]).stdout


def kicad_cli(*args, ok_codes=(0,)) -> subprocess.CompletedProcess:
    r = subprocess.run([str(TOOLBIN / "kicad-cli"), *map(str, args)], capture_output=True, text=True)
    if r.returncode not in ok_codes:
        raise StageError(f"kicad-cli {' '.join(map(str, args))} -> {r.returncode}\n{r.stdout}\n{r.stderr}")
    return r


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem + "_" + path.parent.name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "tools"))
    spec.loader.exec_module(mod)
    return mod


def yload(path: Path, default=None):
    return (yaml.safe_load(path.read_text()) if path.exists() else None) or (default if default is not None else {})


class Board:
    def __init__(self, name: str):
        self.name = name
        self.dir = ROOT / "boards" / name
        if not self.dir.is_dir():
            raise StageError(f"no such board: {self.dir}")
        self.cfg = yload(self.dir / "board.yaml")
        self.build = self.dir / "build"
        self.reports = self.build / "reports"
        self.renders = self.build / "renders"
        self.fab = self.build / "fab"
        self.work = self.build / "work"          # intermediate, gitignored
        for d in (self.reports, self.renders, self.fab, self.work):
            d.mkdir(parents=True, exist_ok=True)
        self.pcb = self.work / f"{name}.kicad_pcb"
        self.origin = self.cfg.get("origin", [100.0, 100.0])

    @property
    def tier(self) -> str:
        return self.cfg.get("assembly_tier", "economic")

    def rules(self) -> dict:
        allr = yload(ROOT / "toolchain" / "rules" / "jlc.yaml")
        base = dict(allr["2layer" if self.cfg.get("layers", 2) <= 2 else "multilayer"])
        base.update(self.cfg.get("rules", {}))
        return base

    def assembly_rules(self) -> dict:
        return yload(ROOT / "toolchain" / "rules" / "jlc.yaml")["assembly"][self.tier]


# ---------------------------------------------------------------------------- stages

def _winpath(p: Path) -> str:
    """Windows path for Windows KiCad, with forward slashes (safe inside KiCad S-expression strings)."""
    return subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip().replace("\\", "/")


def stage_circuit(b: Board) -> dict:
    mod = load_module(b.dir / "circuit.py")
    c = mod.circuit()
    issues = c.validate()
    c.write(b.work / "netlist.json")
    res = {"issues": issues, "assertions": c.assertions,
           "ok": not any(i["severity"] == "error" for i in issues)}
    (b.reports / "circuit.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def stage_schematic(b: Board) -> dict:
    """circuit -> generated .kicad_sch (+ ERC, pin table, render). Harvests the layout first if the
    previous schematic was edited in KiCad (see pcbkit/schematic.py for who owns what)."""
    from . import schematic as sch
    from .render import _keep_if_same
    import cairosvg
    netlist = json.loads((b.work / "netlist.json").read_text())
    layout_path = b.dir / "schematic.yaml"
    layout = yload(layout_path)
    path, rec_path = b.work / f"{b.name}.kicad_sch", b.work / "schematic_gen.json"
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    harvested = False
    if path.exists() and rec.get("sha") and sch.sha(path.read_text(encoding="utf-8")) != rec["sha"]:
        got = sch.harvest(path.read_text(encoding="utf-8"), set(rec.get("auto_uuids", [])))
        keys = {p["ref"] for p in netlist["parts"]} | {f"PWR_FLAG:{n}" for n in netlist.get("power_flags", [])}
        layout = {"symbols": {k: v for k, v in got["symbols"].items() if k in keys},
                  **{k: got[k] for k in ("wires", "labels", "junctions", "texts") if k in got}}
        sch.write_layout(layout_path, layout)
        harvested = True
    gen = sch.Generator(b.name, netlist, layout)
    text, extra = gen.build()
    path.write_text(text, encoding="utf-8", newline="\n")
    (b.work / "pcbkit.kicad_sym").write_text(extra["symlib"], encoding="utf-8", newline="\n")
    (b.work / "sym-lib-table").write_text(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "pcbkit")(type "KiCad")(uri "${KIPRJMOD}/pcbkit.kicad_sym")'
        '(options "")(descr "generated by pcbkit"))\n)\n', newline="\n")
    # repo-local footprint libraries (lib/footprints/<Lib>.pretty), so ERC can resolve their footprint links
    fp_libs = "".join(
        f'\t(lib (name "{d.stem}")(type "KiCad")(uri "{_winpath(d)}")(options "")(descr "pcb-lab lib/footprints"))\n'
        for d in sorted((ROOT / "lib" / "footprints").glob("*.pretty")))
    (b.work / "fp-lib-table").write_text(f"(fp_lib_table\n\t(version 7)\n{fp_libs})\n", newline="\n")
    rec_path.write_text(json.dumps({"sha": sch.sha(text), "auto_uuids": gen.auto_uuids}))
    # kicad-cli only reads sym-lib-table/fp-lib-table inside a project: make sure one exists before ERC
    # (the board stage replaces it with the one SaveBoard writes).
    pro = b.work / f"{b.name}.kicad_pro"
    if not pro.exists():
        pro.write_text(json.dumps({"meta": {"filename": pro.name, "version": 3}}), encoding="utf-8", newline="\n")
    # ERC (KiCad pin electrical types), committed without date/uuids
    raw = b.work / "erc.json"
    kicad_cli("sch", "erc", "--format", "json", "--severity-all", "--units", "mm", "-o", raw, path, ok_codes=(0, 5))
    erc = json.loads(raw.read_text(encoding="utf-8"))
    erc.pop("date", None)
    erc.pop("source", None)
    viol = []
    for sheet in erc.get("sheets", []):
        for v in sheet.get("violations", []):
            for it in v.get("items", []):
                it.pop("uuid", None)
            viol.append(v)
    viol.sort(key=lambda v: json.dumps(v, sort_keys=True))
    (b.reports / "erc.json").write_text(json.dumps({"kicad_version": erc.get("kicad_version"), "violations": viol},
                                                   indent=1) + "\n")
    # KiCad's own reading of the drawing must equal circuit.py, pad for pad
    knet = b.work / "schematic.net"
    kicad_cli("sch", "export", "netlist", "--format", "kicadsexpr", "-o", knet, path)
    gen.findings += sch.compare_netlist(knet.read_text(encoding="utf-8"), netlist)
    # render: SVG -> PNG (kept unless pixels change)
    svgdir = b.work / "sch_svg"
    shutil.rmtree(svgdir, ignore_errors=True)
    kicad_cli("sch", "export", "svg", "-o", svgdir, path)
    svg = next(svgdir.glob("*.svg"))
    tmp = b.work / "schematic.png"
    cairosvg.svg2png(url=str(svg), write_to=str(tmp), output_width=2400, background_color="white")
    _keep_if_same(tmp, b.renders / "schematic.png", tol_px=0)
    shutil.copy(svg, b.work / "schematic.svg")
    res = {"harvested": harvested, "findings": gen.findings, "pin_table": gen.pin_table,
           "erc_violations": len(viol), "power_flags": netlist.get("power_flags", [])}
    (b.reports / "schematic.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    errs = [f["msg"] for f in gen.findings if f["severity"] == "error"]
    return {"harvested": harvested, "erc_violations": len(viol), "errors": len(errs), "first_errors": errs[:5]}


def stage_geometry(b: Board) -> dict:
    mod = load_module(b.dir / "mechanical" / "outline.py")
    g = mod.board()

    def coords(p):
        return [list(map(float, xy)) for xy in (p.exterior.coords if hasattr(p, "exterior") else p)]

    geo = {
        "outline": coords(g["outline"]),
        "cutouts": [coords(c) for c in g.get("cutouts", [])],
        "keepouts": [{**k, "polygon": coords(k["polygon"])} for k in g.get("keepouts", [])],
        "height_zones": [{**h, "polygon": coords(h["polygon"])} for h in g.get("height_zones", [])],
    }
    (b.work / "geometry.json").write_text(json.dumps(geo, indent=1))
    return geo


def stage_board(b: Board) -> dict:
    """circuit + geometry + placement + routing intent -> unrouted .kicad_pcb"""
    netlist = json.loads((b.work / "netlist.json").read_text())
    geo = json.loads((b.work / "geometry.json").read_text())
    placement = yload(b.dir / "placement.yaml")
    routing = yload(b.dir / "routing.yaml")
    classes = {k: v for k, v in netlist["net_classes"].items()}
    classes.setdefault("Default", {"track_width": 0.2, "clearance": 0.2, "via_diameter": 0.6, "via_drill": 0.3})
    win = lambda p: subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True).stdout.strip()  # noqa: E731
    for p in netlist["parts"]:
        model = p.get("meta", {}).get("model")
        if model:
            # "${KICAD10_3DMODEL_DIR}/..." = a stock KiCad model (resolved by KiCad); else a repo path
            model["path_win"] = model["path"] if model["path"].startswith("${") else win(ROOT / model["path"])
        lib = p["footprint"].split(":", 1)[0]
        local = ROOT / "lib" / "footprints" / f"{lib}.pretty"
        if local.is_dir():
            p["footprint_path"] = subprocess.run(["wslpath", "-w", str(local)], capture_output=True, text=True).stdout.strip()
    job = {
        "board_path": win(b.pcb), "report_path": win(b.work / "board_build.json"),
        "origin": b.origin, "silk_refs": b.cfg.get("silk_refs", True), "layers": b.cfg.get("layers", 2), "thickness": b.cfg.get("thickness", 1.6),
        "rules": b.rules(), "net_classes": classes, "nets": netlist["nets"],
        "parts": netlist["parts"], "geometry": geo,
        "placement": placement.get("parts", {}),
        "tracks": routing.get("tracks", []), "vias": routing.get("vias", []),
        "zones": routing.get("zones", []),
    }
    jp = b.work / "board_job.json"
    jp.write_text(json.dumps(job, indent=1))
    # NewBoard() loads an existing .kicad_pro and SaveBoard keeps ITS net classes (stale widths/clearances
    # and pattern assignments from the previous build win over circuit.py), so start from no project file.
    for f in (b.pcb, b.pcb.with_suffix(".kicad_pro")):
        if f.exists():
            f.unlink()
    kipy("build_board.py", jp)
    return json.loads((b.work / "board_build.json").read_text())



def _sexpr(text: str):
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            node = stack.pop()
            stack[-1].append(node)
        else:
            stack[-1].append(t)
    return stack[0]


def _canon(node) -> str:
    if isinstance(node, str):
        return node
    atoms = [c for c in node if isinstance(c, str)]
    if atoms and atoms[0] in ("pins",):
        atoms = atoms[:1] + sorted(atoms[1:])
    kids = sorted(_canon(c) for c in node if not isinstance(c, str))
    return "(" + " ".join(atoms + kids) + ")"


def _sexpr_dump(node) -> str:
    return node if isinstance(node, str) else "(" + " ".join(_sexpr_dump(c) for c in node) + ")"


SNAP_ANGLES = {"45": "fortyfive_degree", "90": "ninety_degree", "none": "none"}


def _shuffle_dsn(src: Path, dst: Path, seed: int, snap: str = "45", planes: tuple = ()) -> None:
    """Write a copy of the DSN with component, net and pin order permuted by `seed`.
    Freerouting is deterministic for a given file but sensitive to item order, so this is
    how we get reproducible variety between routing attempts. Seed 0 = canonical order.
    `snap` adds (snap_angle ...) to the structure: KiCad's export has none, and Freerouting then
    routes free-angle (crooked) traces. Default 45: only 0/45/90-degree segments.
    `planes`: layers declared (type power), so Freerouting keeps signals off them (a GND pour alone
    does not: it routed NRST/SWDIO through the In1 plane of rebot-ctrl)."""
    import random
    text = src.read_text(encoding="utf-8")
    rng = random.Random(seed)
    tree = _sexpr(text.replace('(string_quote ")', "(string_quote QQ)"))[0]

    def walk(node):
        # canonical order first (KiCad's export order is random), then the seeded permutation
        if not isinstance(node, list) or not node:
            return
        head = node[0]
        if head in ("placement", "network", "pins") or (head == "component" and len(node) > 2):
            first = 2 if head == "component" else 1
            kids = sorted(node[first:], key=_sexpr_dump)
            if seed:
                rng.shuffle(kids)
            node[first:] = kids
        for c in node[1:]:
            walk(c)

    walk(tree)
    for node in tree:
        if isinstance(node, list) and node and node[0] == "structure":
            node[:] = [c for c in node if not (isinstance(c, list) and c and c[0] == "snap_angle")]
            node.append(["snap_angle", SNAP_ANGLES[snap]])
            for lay in node:
                if isinstance(lay, list) and lay and lay[0] == "layer" and len(lay) > 1 and lay[1] in planes:
                    for c in lay:
                        if isinstance(c, list) and c and c[0] == "type":
                            c[1:] = ["power"]
    dst.write_text(_sexpr_dump(tree).replace("(string_quote QQ)", '(string_quote ")'), encoding="utf-8")


def _dsn_fingerprint(dsn: Path) -> str:
    """KiCad's DSN export is content-stable but not order-stable (component, net and pin
    order vary run to run), so hash a canonical form: sub-expressions sorted, pin lists sorted,
    and the first atom (the file path) dropped."""
    text = dsn.read_text(encoding="utf-8").replace('(string_quote ")', "(string_quote dq)")
    tree = _sexpr(text)[0]
    # drop the file path and the (parser ...) header (it carries host_version, so a KiCad
    # update would otherwise invalidate every lock without any design change)
    tree = [tree[0]] + [c for c in tree[2:] if not (isinstance(c, list) and c and c[0] == "parser")]
    return hashlib.sha256(_canon(tree).encode()).hexdigest()


def stage_route(b: Board, reroute: bool = False) -> dict:
    """Autoroute with Freerouting, behind a lock: Freerouting is not deterministic (unseeded
    randomness), so its result is committed as boards/<name>/route.lock.ses together with a
    fingerprint of its input. Same input -> the locked result is reused (identical board);
    changed input or --reroute -> route again and update the lock."""
    routing = yload(b.dir / "routing.yaml")
    auto = routing.get("autoroute", {"enabled": True})
    if not auto.get("enabled", True):
        return {"autorouted": False}
    dsn, ses = b.work / f"{b.name}.dsn", b.work / f"{b.name}.ses"
    lock_json, lock_ses = b.dir / "route.lock.json", b.dir / "route.lock.ses"
    for f in (dsn, ses):
        f.unlink(missing_ok=True)
    kipy("specctra.py", "export", b.pcb, dsn)
    snap = str(auto.get("snap_angle", "45"))
    planes = tuple(auto.get("plane_layers", []))
    fp = _dsn_fingerprint(dsn) + ("" if snap == "none" else f"+snap{snap}") + "".join(f"+plane{p}" for p in planes)
    lock = json.loads(lock_json.read_text()) if lock_json.exists() else {}
    if not reroute and lock.get("fingerprint") == fp and lock_ses.exists():
        kipy("specctra.py", "import", b.pcb, lock_ses)
        _straighten(b, b.pcb)
        return {"autorouted": True, "source": "route.lock (input unchanged)", "routed_at": lock.get("routed_at")}
    # Freerouting is random: route several times and keep the cleanest result (routeq.score:
    # jogs dominate, then vias, bends, length). The winner becomes the new lock.
    from . import routeq
    t0 = time.time()
    attempts = int(auto.get("attempts", 5))
    results, log = [], []
    for i in range(attempts):
        ses_i = b.work / f"{b.name}.attempt{i}.ses"
        ses_i.unlink(missing_ok=True)
        dsn_i = b.work / f"{b.name}.attempt{i}.dsn"
        _shuffle_dsn(dsn, dsn_i, seed=i, snap=snap, planes=planes)
        try:
            r = run([TOOLBIN / "freerouting", "-de", dsn_i, "-do", ses_i, "-mp", auto.get("max_passes", 100), "-mt", 1],
                    timeout=auto.get("timeout_s", 600), check=False)
            log.append(f"=== attempt {i}\n{r.stdout}{r.stderr}")
        except subprocess.TimeoutExpired:   # one slow attempt must not kill the build; the others still count
            log.append(f"=== attempt {i}\ntimed out after {auto.get('timeout_s', 600)} s")
            continue
        if not ses_i.exists():
            continue
        trial = b.work / f"{b.name}.attempt{i}.kicad_pcb"
        shutil.copy(b.pcb, trial)
        kipy("specctra.py", "import", trial, ses_i)
        _straighten(b, trial)
        tj = b.work / f"attempt{i}.json"
        kipy("dump.py", trial, tj, *b.origin)
        d = json.loads(tj.read_text())
        q = routeq.analyze(d)
        results.append({"attempt": i, "score": round(routeq.score(d), 1), "unrouted": d["totals"].get("unrouted"), "jogs": len(q["jogs"]),
                        "vias": d["totals"]["vias"], "bends": q["bend_total"],
                        "length": d["totals"]["track_length"], "ses": ses_i})
    (b.work / "freerouting.log").write_text("\n".join(log))
    if not results:
        raise StageError(f"freerouting produced no SES in {attempts} attempts (see {b.work / 'freerouting.log'})")
    best = min(results, key=lambda x: x["score"])
    shutil.copy(best["ses"], ses)
    kipy("specctra.py", "import", b.pcb, ses)
    _straighten(b, b.pcb)
    shutil.copy(ses, lock_ses)
    for x in results:
        x.pop("ses")
    lock_json.write_text(json.dumps({"fingerprint": fp, "routed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                     "freerouting": "see toolchain/versions.env",
                                     "chosen": best["attempt"], "attempts": results}, indent=1) + "\n")
    return {"autorouted": True, "source": f"freerouting: best of {len(results)} (attempt {best['attempt']}, "
                                          f"{best['jogs']} jogs, {best['vias']} vias)",
            "seconds": round(time.time() - t0, 1)}


def _straighten(b: Board, pcb: Path) -> dict:
    """Deterministic jog removal (kijobs/straighten.py), clearance-checked in KiCad."""
    out = kipy("straighten.py", pcb, b.work / "geometry.json", *b.origin, b.rules()["copper_edge_clearance"])
    return json.loads(out.strip().splitlines()[-1])


def stage_stitch(b: Board) -> list[str]:
    out = []
    for s in yload(b.dir / "routing.yaml").get("stitch", []):
        out.append(kipy("stitch.py", b.pcb, s["net"], s.get("pitch", 2.5), s.get("via_diameter", 0.6),
                        s.get("via_drill", 0.3), s.get("edge_margin", 1.0)).strip())
    return out


def stage_dump(b: Board) -> dict:
    out = b.reports / "board.json"
    kipy("dump.py", b.pcb, out, *b.origin)
    return json.loads(out.read_text())


def build(name: str, reroute: bool = False) -> dict:
    b = Board(name)
    res = {"circuit": stage_circuit(b)}
    if not res["circuit"]["ok"]:
        raise StageError("circuit has errors:\n" + "\n".join(i["msg"] for i in res["circuit"]["issues"]))
    res["schematic"] = stage_schematic(b)
    stage_geometry(b)
    res["board"] = stage_board(b)
    res["route"] = stage_route(b, reroute)
    res["stitch"] = stage_stitch(b)
    stage_dump(b)
    # .kicad_prl is per-user GUI view state; the one pcbnew writes headless can leave KiCad
    # showing an empty canvas. Let the GUI start from its own defaults instead.
    b.pcb.with_suffix(".kicad_prl").unlink(missing_ok=True)
    shutil.copy(b.pcb, b.fab / b.pcb.name)
    return res


def schematic(name: str) -> dict:
    """Circuit + schematic only (no board): fast enough to iterate on wiring before any layout."""
    b = Board(name)
    c = stage_circuit(b)
    if not c["ok"]:
        raise StageError("circuit has errors:\n" + "\n".join(i["msg"] for i in c["issues"]))
    return stage_schematic(b)
