"""DSN export / SES import for Freerouting. Runs under KiCad's Python.

usage: kipy specctra.py export BOARD.kicad_pcb OUT.dsn
       kipy specctra.py import BOARD.kicad_pcb IN.ses   (imports, refills zones, saves)
"""
import sys

import pcbnew

mode, board_path, other = sys.argv[1:4]
board = pcbnew.LoadBoard(board_path)
if mode == "export":
    ok = pcbnew.ExportSpecctraDSN(board, other)
elif mode == "import":
    ok = pcbnew.ImportSpecctraSES(board, other)
    if ok:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(board_path, board)
else:
    raise SystemExit(f"unknown mode {mode}")
if not ok:
    raise SystemExit(f"specctra {mode} failed")
print(f"specctra {mode} ok")
