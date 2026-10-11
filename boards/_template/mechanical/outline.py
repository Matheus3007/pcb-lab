"""Board outline, cutouts, holes, keepouts and height zones for this board.

Read by tools/outline (planned). Must define `board()` returning a dict:
  outline:     list of (x, y) mm, closed polygon (or a shapely Polygon)
  cutouts:     list of polygons (internal routed holes, >= 1.0 mm wide)
  holes:       list of {"at": (x, y), "drill": mm, "plated": bool}
  keepouts:    list of {"polygon": [...], "no": ["parts", "tracks", "vias", "copper"]}
  height_zones: list of {"polygon": [...], "side": "top"|"bottom", "max_mm": float}

When chassis CAD exists in mechanical/chassis/, derive geometry from it here instead
of typing numbers, and say which feature each value comes from.
"""


def board():
    w, h = 30.0, 20.0  # placeholder
    return {
        "outline": [(0, 0), (w, 0), (w, h), (0, h)],
        "cutouts": [],
        "holes": [],
        "keepouts": [],
        "height_zones": [],
    }
