"""Review dashboard (build/review/index.html) and gate packets (build/review/gate-N.md).

The dashboard is static HTML next to the renders; open it with VS Code's Live Preview and
it refreshes on every build.
"""
from __future__ import annotations

import html
import json
import time

from .pipeline import Board, yload

VIEWS = ["schematic", "3d_iso", "3d_top", "3d_bottom", "top", "bottom", "placement", "copper_top", "copper_bottom"]


def _esc(s) -> str:
    return html.escape(str(s))


def dashboard(name: str) -> str:
    b = Board(name)
    rev = b.build / "review"
    rev.mkdir(exist_ok=True)
    chk = json.loads((b.reports / "checks.json").read_text())
    st = chk["stats"]
    imgs = [v for v in VIEWS if (b.renders / f"{v}.png").exists()]
    rows = []
    for f in sorted(chk["findings"], key=lambda f: (["error", "warning", "info", "ok"].index(f["severity"]), f["check"])):
        sev = "waived" if "waived" in f else f["severity"]
        rows.append(f"<tr class='{sev}'><td>{_esc(sev)}</td><td><code>{_esc(f['check'])}</code></td>"
                    f"<td>{_esc(f['msg'])}{(' — <i>' + _esc(f['waived']) + '</i>') if 'waived' in f else ''}</td></tr>")
    bom = "".join(
        f"<tr><td>{_esc(', '.join(r['refs']))}</td><td>{_esc(r['value'])}</td><td>{_esc(r['mpn'])}</td>"
        f"<td>{_esc(r['lcsc'])}</td><td class='tier-{_esc(r['tier'])}'>{_esc(r['tier'])}</td>"
        f"<td>{r['stock']:,}</td><td>${r['unit_price_usd']}</td></tr>" for r in chk["bom"])
    gallery = "".join(f"<figure><a href='../renders/{v}.png'><img src='../renders/{v}.png?t={int(time.time())}'></a>"
                      f"<figcaption>{v}</figcaption></figure>" for v in imgs)
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>{_esc(name)} review</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--bg:#0f141a;--fg:#e6e9ee;--mut:#8b96a5;--card:#18202a;--line:#263241;--ok:#3fb27f;--err:#e5534b;--warn:#d4a72c}}
body{{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;margin:0;padding:20px}}
h1{{margin:0 0 4px}} .mut{{color:var(--mut)}} code{{font-size:12px}}
.badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-weight:600;background:{'var(--ok)' if chk['pass'] else 'var(--err)'};color:#000}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px;margin:16px 0}}
figure{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}}
figure img{{width:100%;display:block}} figcaption{{padding:6px 10px;color:var(--mut)}}
table{{border-collapse:collapse;width:100%;margin:8px 0 20px}} td,th{{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}}
tr.error td:first-child{{color:var(--err);font-weight:600}} tr.warning td:first-child{{color:var(--warn)}}
tr.ok td:first-child{{color:var(--ok)}} tr.waived td{{color:var(--mut)}} .tier-extended{{color:var(--warn)}}
</style></head><body>
<h1>{_esc(name)} <span class="badge">{'PASS' if chk['pass'] else 'FAIL'}</span></h1>
<div class="mut">{chk['errors']} errors · {chk['warnings']} warnings · {chk['waived']} waived ·
board {st['size_mm'][0]} × {st['size_mm'][1]} mm · {st['parts']} footprints · {st['tracks']} segments ·
{st['vias']} vias · {st['track_length']} mm copper · built {time.strftime('%Y-%m-%d %H:%M')}</div>
<div class="gallery">{gallery}</div>
<h2>Checks</h2><table><tr><th>severity</th><th>check</th><th>detail</th></tr>{''.join(rows)}</table>
<h2>BOM (JLC)</h2><table><tr><th>refs</th><th>value</th><th>MPN</th><th>LCSC</th><th>tier</th><th>stock</th><th>unit</th></tr>{bom}</table>
</body></html>"""
    (rev / "index.html").write_text(page, encoding="utf-8")
    return str(rev / "index.html")


def gate(name: str, n: int) -> str:
    """Write the review packet for gate n (see docs/review-gates.md)."""
    b = Board(name)
    chk = json.loads((b.reports / "checks.json").read_text())
    netlist = json.loads((b.work / "netlist.json").read_text())
    L = [f"# {name}: review gate {n}", f"_generated {time.strftime('%Y-%m-%d %H:%M')} · checks {'PASS' if chk['pass'] else 'FAIL'}_", ""]
    open_items = [f for f in chk["findings"] if f["severity"] in ("error", "warning") and "waived" not in f]
    if n == 1:   # gate 1 is before outline/placement: layout findings are noise there (they belong to gate 2)
        open_items = [f for f in open_items
                      if not f["check"].startswith(("drc/", "placement/", "routing/", "current/", "models/", "mech"))]
    if n == 2:   # gate 2 is before routing: unrouted connections belong to gate 3
        open_items = [f for f in open_items if f["check"] not in ("drc/unconnected", "current/width")]
    if open_items:
        L += ["## Open items (read first)"] + [f"- **{f['severity']}** `{f['check']}` {f['msg']}" for f in open_items] + [""]
    if n == 1:
        L += ["## BOM", "| refs | value | MPN | LCSC | tier | stock | unit $ |", "|---|---|---|---|---|---|---|"]
        L += [f"| {', '.join(r['refs'])} | {r['value']} | {r['mpn']} | {r['lcsc']} | {r['tier']} | {r['stock']:,} | {r['unit_price_usd']} |" for r in chk["bom"]]
        sj = json.loads((b.reports / "schematic.json").read_text()) if (b.reports / "schematic.json").exists() else None
        if sj:
            L += ["", "## Schematic (generated from circuit.py; read it next to the datasheets)",
                  "![schematic](../renders/schematic.png)", ""]
            L += [f"- {'✓' if f['severity'] == 'ok' else '✗'} `{f['check']}` {f['msg']}" for f in sj["findings"]
                  if f["severity"] in ("ok", "error", "warning")]
            L += ["", "## Pin tables (pad → KiCad symbol name / parts.yaml name → electrical type → net)"]
            for ref, rows in sj["pin_table"].items():
                if not rows:
                    continue
                L += ["", f"**{ref}**", "", "| pad | symbol | ours | type | net |", "|---|---|---|---|---|"]
                L += [f"| {r['pad']} | {r['symbol_name'] or '—'} | {r['name']} | {r['type']} | {r['net']} |" for r in rows]
        L += ["", "## Pinout evidence (ICs and connectors)"]
        for p in netlist["parts"]:
            m = p["meta"]
            if m.get("lib_key"):
                L.append(f"- **{p['ref']}** {m['lib_key']} ({p['lcsc']}): {m.get('pinout_source', 'MISSING')} — verified {m.get('pinout_verified', 'NO')}")
                L.append(f"  - pin map: " + ", ".join(f"{k}={'/'.join(v)}" for k, v in p["pins"].items()))
                if m.get("notes"):
                    L.append(f"  - note: {m['notes']}")
        L += ["", "## Design assertions"] + [f"- {'✓' if a['ok'] else '✗'} {a['name']}: {a['value']:.4g} {a['unit']} (allowed {a['min']:.4g} … {a['max']:.4g})"
                                             for a in json.loads((b.reports / 'circuit.json').read_text())["assertions"]]
        L += ["", "## Nets", *[f"- `{k}` ({v['class']}): {', '.join(v['pins'])}" for k, v in netlist["nets"].items()],
              f"- NC: {', '.join(netlist['no_connect']) or '—'}"]
    if n == 2:
        L += ["## Renders", "![placement](../renders/placement.png)", "![3d iso](../renders/3d_iso.png)",
              "![3d top](../renders/3d_top.png)", "![3d bottom](../renders/3d_bottom.png)", "",
              "## Placement rules"] + [f"- {'✓' if f['severity'] == 'ok' else '✗'} {f['msg']}" for f in chk["findings"] if f["check"].startswith("placement/")]
        L += ["", "## Placement intent (from placement.yaml)"]
        for ref, spot in yload(b.dir / "placement.yaml").get("parts", {}).items():
            L.append(f"- {ref}: {spot}")
    if n == 3:
        L += ["## Renders", "![top](../renders/top.png)", "![bottom](../renders/bottom.png)",
              "![copper top](../renders/copper_top.png)", "![copper bottom](../renders/copper_bottom.png)",
              "![3d iso](../renders/3d_iso.png)", "", "## Fab files (build/fab/)"]
        L += [f"- {p.name}" for p in sorted(b.fab.iterdir())]
        cor = json.loads((b.fab / "cpl_corrections.json").read_text()) if (b.fab / "cpl_corrections.json").exists() else []
        L += ["", "## CPL rotation corrections applied (UNVERIFIED until you check JLC's preview)"]
        L += [f"- {c['ref']} `{c['footprint']}`: {c['rotation_delta']:+g}° (rule `{c['rule']}`, {c.get('source', 'hint')})" for c in cor] or ["- none"]
        cost = sum((r["unit_price_usd"] or 0) * len(r["refs"]) for r in chk["bom"])
        L += ["", f"Parts cost per board ≈ ${cost:.2f} + extended-part fees ({sum(r['tier'] == 'extended' for r in chk['bom'])} unique extended)",
              "", "## Before paying", "1. Upload the gerber zip; inspect JLC's Gerber viewer (outline, cutouts, drills).",
              "2. Upload BOM + CPL; check EVERY part's rotation/polarity in JLC's placement preview.",
              "3. Record corrections in lib/jlc_rotations.csv (top of file), rebuild, re-upload.",
              "4. After ordering: `git tag <board>/vX.Y` and note the order number in spec.md."]
    out = b.build / "review" / f"gate-{n}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return str(out)
