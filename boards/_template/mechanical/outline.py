"""Board outline, cutouts, holes, keepouts and height zones for this board.

Read by pcbkit.pipeline.stage_geometry. Must define `board()` returning a dict:
  outline:     shapely Polygon or list of (x, y) mm; +Y down, origin top-left
  cutouts:     list of polygons (internal routed holes, >= 1.0 mm wide)
  (mounting holes are parts: MountingHole_* in lib/parts.yaml, placed in placement.yaml)
  keepouts:    list of {"polygon": ..., "layers": ["F.Cu","B.Cu"], "no": ["parts","tracks","vias","copper","pads"]}
  height_zones: list of {"polygon": [...], "side": "top"|"bottom", "max_mm": float}

When chassis CAD exists in mechanical/chassis/, derive geometry from it here instead
of typing numbers, and say which feature each value comes from.
"""


def board():
    w, h = 30.0, 20.0  # placeholder
    return {
        "outline": [(0, 0), (w, 0), (w, h), (0, h)],
        "cutouts": [],
        "keepouts": [],
        "height_zones": [],
    }
