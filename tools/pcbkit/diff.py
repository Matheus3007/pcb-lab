"""Semantic board diff against a git ref, using the committed build/reports/board.json and
renders (so no rebuild of the old version is needed).

Writes build/work/diff.md and build/work/diff_<view>.png (old | new side by side).
"""
from __future__ import annotations

import io
import json
import subprocess

from PIL import Image, ImageDraw

from .pipeline import ROOT, Board


def _git_show(ref: str, path) -> bytes | None:
    rel = path.relative_to(ROOT).as_posix()
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{rel}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def diff(name: str, ref: str = "HEAD") -> str:
    b = Board(name)
    new = json.loads((b.reports / "board.json").read_text())
    raw = _git_show(ref, b.reports / "board.json")
    if raw is None:
        return f"no committed board.json for {name} at {ref}"
    old = json.loads(raw)
    L = [f"# {name}: diff {ref} → working tree", ""]
    if old["size_mm"] != new["size_mm"]:
        L.append(f"- board size {old['size_mm']} → {new['size_mm']}")
    of = {f["ref"]: f for f in old["footprints"]}
    nf = {f["ref"]: f for f in new["footprints"]}
    for r in sorted(set(nf) - set(of)):
        L.append(f"- **added** {r} ({nf[r]['footprint']}) at {nf[r]['at']}")
    for r in sorted(set(of) - set(nf)):
        L.append(f"- **removed** {r}")
    for r in sorted(set(of) & set(nf)):
        a, c = of[r], nf[r]
        ch = []
        if a["at"] != c["at"]:
            ch.append(f"moved {a['at']} → {c['at']}")
        if a["rot"] != c["rot"]:
            ch.append(f"rot {a['rot']} → {c['rot']}")
        if a["side"] != c["side"]:
            ch.append(f"side {a['side']} → {c['side']}")
        if a["footprint"] != c["footprint"]:
            ch.append(f"footprint {a['footprint']} → {c['footprint']}")
        if a["value"] != c["value"]:
            ch.append(f"value {a['value']} → {c['value']}")
        pa = {p["num"]: p["net"] for p in a["pads"]}
        pc = {p["num"]: p["net"] for p in c["pads"]}
        for k in sorted(set(pa) | set(pc)):
            if pa.get(k) != pc.get(k):
                ch.append(f"pad {k} net {pa.get(k)} → {pc.get(k)}")
        if ch:
            L.append(f"- {r}: " + "; ".join(ch))
    L += ["", "| net | length old → new (mm) | vias old → new |", "|---|---|---|"]
    for n in sorted(set(old["nets"]) | set(new["nets"])):
        o, c = old["nets"].get(n, {}), new["nets"].get(n, {})
        if (o.get("track_length"), o.get("vias")) != (c.get("track_length"), c.get("vias")):
            L.append(f"| {n} | {o.get('track_length', 0)} → {c.get('track_length', 0)} | {o.get('vias', 0)} → {c.get('vias', 0)} |")
    ot, nt = old["totals"], new["totals"]
    L += ["", f"totals: segments {ot['tracks']} → {nt['tracks']}, vias {ot['vias']} → {nt['vias']}, "
              f"copper {ot['track_length']} → {nt['track_length']} mm"]
    for view in ("top", "placement", "3d_iso"):
        cur = b.renders / f"{view}.png"
        prev = _git_show(ref, cur)
        if prev and cur.exists():
            a, c = Image.open(io.BytesIO(prev)).convert("RGB"), Image.open(cur).convert("RGB")
            h = max(a.height, c.height)
            img = Image.new("RGB", (a.width + c.width + 20, h + 30), "#202020")
            img.paste(a, (0, 30))
            img.paste(c, (a.width + 20, 30))
            d = ImageDraw.Draw(img)
            d.text((10, 8), f"{ref}", fill="white")
            d.text((a.width + 30, 8), "working tree", fill="white")
            out = b.work / f"diff_{view}.png"
            img.save(out)
            L.append(f"\n![{view}]({out.name})")
    text = "\n".join(L) + "\n"
    (b.work / "diff.md").write_text(text, encoding="utf-8")
    return text
