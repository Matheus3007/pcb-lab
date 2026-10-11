"""pipeline-demo outline: 30 x 24 mm rounded rectangle, semicircular notch on the
right edge and an internal slot, to exercise non-rectangular geometry.

Board coordinates: mm, origin top-left, +X right, +Y down (KiCad convention).
"""
from shapely.geometry import LineString, Point, box

W, H = 30.0, 24.0
CORNER_R = 2.0
NOTCH = dict(center=(W, 12.0), r=4.0)      # bite out of the right edge
SLOT = dict(x=4.0, y0=13.0, y1=20.0, w=2.0)  # internal routed slot (JLC: >= 1.0 mm)


def board():
    outline = box(CORNER_R, CORNER_R, W - CORNER_R, H - CORNER_R).buffer(CORNER_R, quad_segs=8)
    outline = outline.difference(Point(*NOTCH["center"]).buffer(NOTCH["r"], quad_segs=16))
    slot = LineString([(SLOT["x"], SLOT["y0"]), (SLOT["x"], SLOT["y1"])]).buffer(SLOT["w"] / 2, quad_segs=8)
    return {
        "outline": outline.simplify(0.001),
        "cutouts": [slot],
        "keepouts": [],
        "height_zones": [],
    }
