"""Stage 6: renders for agent + human review.

2D views are kicad-cli SVG plots rasterized to PNG (Claude reads PNGs); 3D views come
from kicad-cli's renderer; a GLB is exported for interactive 3D viewing in VS Code.
"""
from __future__ import annotations

import cairosvg

from .pipeline import Board, kicad_cli

PX_PER_MM = 40
BG = "#0b1724"

VIEWS_2D = {
    # name: (layers, extra args)
    "top": ("F.Cu,F.Mask,F.Silkscreen,Edge.Cuts", []),
    "bottom": ("B.Cu,B.Mask,B.Silkscreen,Edge.Cuts", ["--mirror"]),
    "placement": ("F.Fab,F.Courtyard,Edge.Cuts", ["--sketch-pads-on-fab-layers", "--crossout-DNP-footprints-on-fab-layers"]),
    "copper_top": ("F.Cu,Edge.Cuts", []),
    "copper_bottom": ("B.Cu,Edge.Cuts", ["--mirror"]),
}
VIEWS_3D = {
    "3d_top": ["--side", "top"],
    "3d_bottom": ["--side", "bottom"],
    "3d_iso": ["--side", "top", "--rotate", "-40,0,30", "--perspective", "--zoom", "0.9"],
}


def render(name: str, three_d: bool = True) -> list[str]:
    b = Board(name)
    size = __import__("json").loads((b.reports / "board.json").read_text())["size_mm"]
    out = []
    for view, (layers, extra) in VIEWS_2D.items():
        svg = b.work / f"{view}.svg"
        kicad_cli("pcb", "export", "svg", "--mode-single", "--page-size-mode", "2",
                  "--exclude-drawing-sheet", "--layers", layers, *extra, "-o", svg, b.pcb)
        png = b.renders / f"{view}.png"
        cairosvg.svg2png(url=str(svg), write_to=str(png),
                         output_width=int((size[0] + 2) * PX_PER_MM), background_color=BG)
        out.append(png.name)
    if three_d:
        for view, args in VIEWS_3D.items():
            png = b.renders / f"{view}.png"
            kicad_cli("pcb", "render", "-o", png, "--width", 1400, "--height", 1050,
                      "--quality", "high", "--background", "opaque", *args, b.pcb)
            out.append(png.name)
        kicad_cli("pcb", "export", "glb", "-f", "--grid-origin", "--subst-models", "--include-tracks", "--include-pads",
                  "--include-zones", "--include-silkscreen", "--include-soldermask",
                  "-o", b.work / f"{name}.glb", b.pcb, ok_codes=(0,))
    return out
