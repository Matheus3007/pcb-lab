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

def stage_circuit(b: Board) -> dict:
    mod = load_module(b.dir / "circuit.py")
    c = mod.circuit()
    issues = c.validate()
    c.write(b.work / "netlist.json")
    res = {"issues": issues, "assertions": c.assertions,
           "ok": not any(i["severity"] == "error" for i in issues)}
    (b.reports / "circuit.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


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
            model["path_win"] = win(ROOT / model["path"])
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
    if b.pcb.exists():
        b.pcb.unlink()
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
    fp = _dsn_fingerprint(dsn)
    lock = json.loads(lock_json.read_text()) if lock_json.exists() else {}
    if not reroute and lock.get("fingerprint") == fp and lock_ses.exists():
        kipy("specctra.py", "import", b.pcb, lock_ses)
        return {"autorouted": True, "source": "route.lock (input unchanged)", "routed_at": lock.get("routed_at")}
    t0 = time.time()
    r = run([TOOLBIN / "freerouting", "-de", dsn, "-do", ses, "-mp", auto.get("max_passes", 100), "-mt", 1],
            timeout=auto.get("timeout_s", 600), check=False)
    (b.work / "freerouting.log").write_text(r.stdout + r.stderr)
    if not ses.exists():
        raise StageError(f"freerouting produced no SES (see {b.work / 'freerouting.log'})")
    kipy("specctra.py", "import", b.pcb, ses)
    shutil.copy(ses, lock_ses)
    summary = re.findall(r"final score: [^,]+, \(([^)]*)\)|final score: ([0-9.]+) \(([^)]*)\)", r.stdout)
    lock_json.write_text(json.dumps({"fingerprint": fp, "routed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                     "freerouting": "see toolchain/versions.env",
                                     "result": next((m[2] for m in summary if m[2]), None)}, indent=1) + "\n")
    return {"autorouted": True, "source": "freerouting (new lock written)", "seconds": round(time.time() - t0, 1)}


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
