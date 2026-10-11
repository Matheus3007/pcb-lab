"""rebot-esc outline: 34 x 21 mm rounded rectangle.

Board coordinates: mm, origin top-left, +X right, +Y down (KiCad convention).
Size from the gate-2 layout: the bottom edge carries the 2x5 carrier header (left, through-hole, its
pads block the top side) and the three motor pads (right); the power stage, driver, MCU and supplies
share the 34 x 15 mm above. The module lies flat on the carrier, so 21 mm of width uses 21 of the carrier's ~30 mm
height (docs/projects/battlebot.md, Board location). No cutouts: the M2 retention hole is a part (H1).
"""
from shapely.geometry import box

W, H = 34.0, 21.0
CORNER_R = 1.0


def board():
    outline = box(CORNER_R, CORNER_R, W - CORNER_R, H - CORNER_R).buffer(CORNER_R, quad_segs=8)
    return {
        "outline": outline.simplify(0.001),
        "cutouts": [],
        "keepouts": [],
        "height_zones": [],
    }
