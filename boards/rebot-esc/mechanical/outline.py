"""rebot-esc outline: 36 x 20 mm rounded rectangle, laid out like an off-the-shelf ESC (B-CUBE 35 x 18).

Board coordinates: mm, origin top-left, +X right, +Y down (KiCad convention).
Left short edge: the keyed 2x5 carrier header (battery + signals in). Right short edge: the three motor
pads in a column, one per phase row. Between them: MCU / driver / supplies, then the power stage as
three rows (VBAT cap -> high-side FET -> low-side FET -> motor pad). The module lies flat on the carrier,
so 20 mm of width uses 20 of the carrier's ~30 mm height. No cutouts: the M2 retention hole is a part (H1).
"""
from shapely.geometry import box

W, H = 36.0, 20.0
CORNER_R = 1.0


def board():
    outline = box(CORNER_R, CORNER_R, W - CORNER_R, H - CORNER_R).buffer(CORNER_R, quad_segs=8)
    return {
        "outline": outline.simplify(0.001),
        "cutouts": [],
        "keepouts": [],
        "height_zones": [],
    }
