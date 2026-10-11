"""python -m pcbkit <command> <board>   (normally called through the Makefile)"""
import argparse
import json
import sys

from . import pipeline


def main() -> int:
    ap = argparse.ArgumentParser(prog="pcbkit")
    ap.add_argument("command", choices=["build", "check", "render", "fab", "report", "gate", "diff", "all", "parts"])
    ap.add_argument("board")
    ap.add_argument("--ref", default="HEAD", help="diff: git ref to compare against")
    ap.add_argument("--fast", action="store_true", help="render/all: skip 3D views")
    ap.add_argument("--gate", type=int, choices=[1, 2, 3], help="gate: which review packet")
    ap.add_argument("--reroute", action="store_true", help="build/all: ignore route.lock and autoroute again")
    ap.add_argument("--refresh", action="store_true", help="parts: refresh JLC stock/price cache")
    a = ap.parse_args()
    try:
        if a.command in ("build", "all"):
            res = pipeline.build(a.board, reroute=a.reroute)
            print(json.dumps({k: v for k, v in res.items() if k != "circuit"}))
        if a.command in ("render", "all"):
            from . import render
            print("renders:", ", ".join(render.render(a.board, three_d=not a.fast)))
        if a.command in ("check", "all"):
            from . import checks, report
            r = checks.check(a.board)
            print((pipeline.Board(a.board).reports / "summary.md").read_text())
            print("dashboard:", report.dashboard(a.board))
            if not r["pass"]:
                return 1
        if a.command == "report":
            from . import report
            print(report.dashboard(a.board))
        if a.command == "gate":
            from . import report
            print(report.gate(a.board, a.gate or 1))
        if a.command == "fab":
            from . import fab
            print(json.dumps(fab.fab(a.board), indent=1))
        if a.command == "diff":
            from . import diff
            print(diff.diff(a.board, a.ref))
        if a.command == "parts":
            from . import jlc
            net = json.loads((pipeline.Board(a.board).work / "netlist.json").read_text())
            for p in net["parts"]:
                if p["lcsc"]:
                    i = jlc.lookup(p["lcsc"], refresh=a.refresh)
                    print(f"{p['ref']:5} {p['lcsc']:9} {i['tier']:9} stock {i['stock']:>10,}  ${i['unit_price_usd']}  {i['mpn']}")
        return 0
    except pipeline.StageError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


sys.exit(main())
