"""rebot-ctrl outline: 30 x 28 mm rounded rectangle.

Board coordinates: mm, origin top-left, +X right, +Y down (KiCad convention).
Taped onto the Flywoo GOKU G45M 4-in-1 (33 x 30 mm), so it must stay inside that outline. The stack
stands in Rebot's rear channel with the ESC's signal edge up (toward the lid): the USB-C and the ESC
connector sit on this board's top edge, the receiver connector on the left edge (the receiver lives on
the robot's left side). No holes: the board is taped.
"""
from shapely.geometry import box

W, H = 30.0, 28.0
CORNER_R = 1.5


def board():
    outline = box(CORNER_R, CORNER_R, W - CORNER_R, H - CORNER_R).buffer(CORNER_R, quad_segs=8)
    return {"outline": outline.simplify(0.001), "cutouts": [], "keepouts": [], "height_zones": []}
