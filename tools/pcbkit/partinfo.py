"""Research helpers for adding parts (used by the add-part skill).

part(lcsc)       JLC info, datasheet PDF, pin-table pages (text + PNG), KiCad footprint candidates
footprint(spec)  pad table, extents, facing hint, 3D model presence, PNG render of a footprint
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from . import jlc
from .pipeline import ROOT, _sexpr, kicad_cli

STOCK = Path("/mnt/c/Program Files/KiCad/10.0/share/kicad")
DS_DIR = ROOT / "lib" / "datasheets"           # gitignored: re-downloadable, not ours to redistribute
PIN_WORDS = re.compile(r"pin\s*(configuration|assignment|description|function|out|definition)|pinout|pin no", re.I)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def footprint_candidates(package: str, limit: int = 12) -> list[str]:
    """Stock footprints whose name contains the package token (e.g. 'SOT-23-3L' -> SOT-23-3)."""
    toks = [t for t in re.split(r"[\s/_(),]+", package or "") if t]
    keys = {_norm(t) for t in toks} | {_norm(re.sub(r"L$", "", t)) for t in toks}
    keys = {k for k in keys if len(k) >= 3}
    hits = []
    for lib in sorted((STOCK / "footprints").glob("*.pretty")):
        for f in lib.glob("*.kicad_mod"):
            n = _norm(f.stem)
            if any(n.startswith(k) or f"_{k}" in "_" + n for k in keys):
                hits.append(f"{lib.stem}:{f.stem}")
    hits.sort(key=lambda h: (len(h.split(":")[1]), h))
    return hits[:limit]


def part(lcsc: str) -> str:
    info = jlc.lookup(lcsc, refresh=True)
    out = [f"# {lcsc}: {info['manufacturer']} {info['mpn']}",
           f"- {info['description']}",
           f"- category: {info.get('category')} · package: {info['package']}",
           f"- JLC tier: **{info['tier']}** · stock {info['stock']:,} · ${info['unit_price_usd']} (as of {info['fetched']})"]
    try:
        pdf = jlc.datasheet(lcsc, DS_DIR / f"{lcsc}.pdf")
        doc = pymupdf.open(pdf)
        out.append(f"- datasheet: {pdf} ({doc.page_count} pages)")
        pages = [i for i in range(min(doc.page_count, 12)) if PIN_WORDS.search(doc[i].get_text())][:3]
        for i in pages:
            png = DS_DIR / f"{lcsc}_p{i + 1}.png"
            doc[i].get_pixmap(dpi=110).save(png)
            text = re.sub(r"\s*\n\s*", " | ", doc[i].get_text())[:2500]
            out += ["", f"## page {i + 1} (image: {png})", text]
        if not pages:
            out.append("- no page mentions a pin table in the first 12 pages; read the PDF images directly")
    except Exception as e:  # noqa: BLE001
        out.append(f"- datasheet: NOT AVAILABLE ({e}); find the manufacturer PDF manually")
    out += ["", "## KiCad stock footprint candidates"] + [f"- {c}" for c in footprint_candidates(info["package"])] \
        + ["", "Next: verify pin table vs footprint pads (`make footprint FP=Lib:Name`), then add to lib/parts.yaml."]
    return "\n".join(out)


def footprint(spec: str, render_dir: Path | None = None) -> str:
    lib, name = spec.split(":", 1)
    path = STOCK / "footprints" / f"{lib}.pretty" / f"{name}.kicad_mod"
    if not path.exists():
        path = ROOT / "lib" / "footprints" / f"{lib}.pretty" / f"{name}.kicad_mod"
    if not path.exists():
        return f"footprint {spec} not found in KiCad stock libs or lib/footprints/"
    txt = path.read_text(encoding="utf-8")
    pads = re.findall(r'\(pad "([^"]*)" (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)\s*\(size ([-\d.]+) ([-\d.]+)\)', txt)

    tree = _sexpr(txt)[0]

    def extent(layer):
        xs, ys = [], []
        for node in tree:
            if not (isinstance(node, list) and node and str(node[0]).startswith("fp_")):
                continue
            if ["layer", f'"{layer}"'] not in [c for c in node if isinstance(c, list)]:
                continue
            stack = [node]
            while stack:
                n = stack.pop()
                for c in n:
                    if isinstance(c, list):
                        if c and c[0] in ("start", "end", "xy", "center", "mid") and len(c) >= 3:
                            xs.append(float(c[1]))
                            ys.append(float(c[2]))
                        else:
                            stack.append(c)
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None

    fab, crt = extent("F.Fab"), extent("F.CrtYd")
    out = [f"# {spec}", f"- file: {path}", "", "| pad | type | shape | x | y | w | h |", "|---|---|---|---|---|---|---|"]
    out += [f"| {n or '(np)'} | {t} | {sh} | {x} | {y} | {w} | {h} |" for n, t, sh, x, y, _r, w, h in pads]
    out += ["", f"- fab body extent (x0,y0,x1,y1): {fab}", f"- courtyard extent: {crt}"]
    smd = [(float(x), float(y)) for n, t, sh, x, y, _r, w, h in pads if t == "smd" and n]
    if smd and fab:
        cx, cy = sum(p[0] for p in smd) / len(smd), sum(p[1] for p in smd) / len(smd)
        bx, by = (fab[0] + fab[2]) / 2, (fab[1] + fab[3]) / 2
        if abs(cy - by) > abs(cx - bx) and abs(cy - by) > 0.5:
            side = "-Y (up)" if cy < by else "+Y (down)"
            out.append(f"- SMD pads cluster toward {side} of the body at rot 0 → a connector's mouth faces the OPPOSITE side")
        elif abs(cx - bx) > 0.5:
            side = "-X (left)" if cx < bx else "+X (right)"
            out.append(f"- SMD pads cluster toward {side} of the body at rot 0 → a connector's mouth faces the OPPOSITE side")
    models = re.findall(r'\(model "([^"]+)"', txt)
    for m in models:
        p = Path(m.replace("${KICAD10_3DMODEL_DIR}", str(STOCK / "3dmodels")))
        out.append(f"- 3D model: {m} → {'present' if p.exists() else 'MISSING (add model: in parts.yaml)'}")
    if not models:
        out.append("- 3D model: none referenced (add model: in parts.yaml)")
    if render_dir:
        render_dir.mkdir(parents=True, exist_ok=True)
        import cairosvg
        kicad_cli("fp", "export", "svg", "--footprint", name, "--layers", "F.Cu,F.Fab,F.CrtYd,F.SilkS",
                  "-o", render_dir, path.parent)
        svg = render_dir / f"{name}.svg"
        if svg.exists():
            png = render_dir / f"{name}.png"
            cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=900, background_color="#0b1724")
            out.append(f"- render: {png}")
    return "\n".join(out)
