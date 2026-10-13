"""rebot-ctrl-v2 outline: rounded rectangle, smaller than v1 (30 x 28 mm).

Board coordinates: mm, origin top-left, +X right, +Y down (KiCad convention).
Taped onto the 4-in-1 ESC (HAKRC 40A: 31 x 30 mm; Flywoo G45M: 33 x 30 mm), so it must stay inside that
outline. The stack stands in Rebot's rear channel with the signal edge up (toward the lid): the ESC connector
(left) and the USB-C (right) sit on this board's top edge, the receiver connector on the left edge. No holes:
the board is taped.
"""
from shapely.geometry import Point, box

W, H = 25.0, 25.0
CORNER_R = 1.0


# Bottom-side test pads (unassembled) cut 1.4 mm holes in the B.Cu GND plane, which is In2.Cu's return path: keep
# other nets' In2 tracks off them (layout/return_path). A notch lets the pad's own net reach its via on In2.
TEST_PADS = {   # name: (x, y, notch direction of the pad's own In2 track, or None)
    "TP1": (8.45, 3.2, "S"), "TP2": (2.0, 3.2, None), "TP3": (4.15, 3.2, "S"), "TP4": (6.3, 3.2, "S"),
    "TP5": (8.2, 8.85, "W"), "TP6": (13.1, 9.25, None),
}


def tp_keepout(x, y, notch):
    k = Point(x, y).buffer(0.85, quad_segs=8)
    if notch == "S":
        k = k.difference(box(x - 0.2, y - 0.3, x + 0.2, y + 1.0))
    elif notch == "W":
        k = k.difference(box(x - 1.0, y - 0.2, x + 0.3, y + 0.2))
    return {"polygon": k.simplify(0.001), "layers": ["In2.Cu"], "no": ["tracks"]}


def board():
    outline = box(CORNER_R, CORNER_R, W - CORNER_R, H - CORNER_R).buffer(CORNER_R, quad_segs=8)
    keepouts = [{**tp_keepout(*v), "name": f"{k} In2 keepout"} for k, v in TEST_PADS.items()]
    return {"outline": outline.simplify(0.001), "cutouts": [], "keepouts": keepouts, "height_zones": []}
