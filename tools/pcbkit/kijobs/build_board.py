"""Generate a .kicad_pcb from a job JSON. Runs under KiCad's Python (toolchain/bin/kipy).

usage: kipy build_board.py job.json

The board is regenerated from scratch every build: nothing in the .kicad_pcb is
hand-maintained. Board coordinates in the job are mm with +X right, +Y DOWN (KiCad
convention), relative to the board origin; they are offset by job["origin"] on the sheet.
"""
import json
import os
import sys

import pcbnew

STOCK_FP = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
LAYER = {
    "F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu,
    "Edge.Cuts": pcbnew.Edge_Cuts, "F.SilkS": pcbnew.F_SilkS, "B.SilkS": pcbnew.B_SilkS,
}


def mm(v):
    return pcbnew.FromMM(float(v))


class Builder:
    def __init__(self, job):
        self.job = job
        self.ox, self.oy = job.get("origin", [100.0, 100.0])
        self.board = pcbnew.NewBoard(job["board_path"])
        self.nets = {}
        self.report = {"placed": [], "warnings": []}

    def pt(self, x, y):
        return pcbnew.VECTOR2I(mm(self.ox + x), mm(self.oy + y))

    # -- setup ---------------------------------------------------------------
    def setup(self):
        b, j = self.board, self.job
        b.SetCopperLayerCount(j.get("layers", 2))
        ds = b.GetDesignSettings()
        ds.SetBoardThickness(mm(j.get("thickness", 1.6)))
        r = j["rules"]
        ds.m_MinClearance = mm(r["min_clearance"])
        ds.m_TrackMinWidth = mm(r["min_track_width"])
        ds.m_ViasMinSize = mm(r["min_via_diameter"])
        ds.m_MinThroughDrill = mm(r["min_drill"])
        ds.m_CopperEdgeClearance = mm(r["copper_edge_clearance"])
        ds.m_HoleToHoleMin = mm(r["hole_to_hole"])
        ds.m_MinSilkTextHeight = mm(r["min_silk_text_height"])
        ds.m_SilkClearance = mm(r["silk_clearance"])
        ds.m_ViasMinAnnularWidth = mm(r["min_annular_ring"])

        ns = ds.m_NetSettings
        default = ns.GetDefaultNetclass()
        d = j["net_classes"].get("Default")
        if d:
            self._apply_class(default, d)
            ns.SetDefaultNetclass(default)   # KiCad 10: edits to the Get'd default are not saved otherwise
        for name, c in j["net_classes"].items():
            if name == "Default":
                continue
            nc = pcbnew.NETCLASS(name)
            self._apply_class(nc, c)
            ns.SetNetclass(name, nc)
        for net, info in j["nets"].items():
            if info["class"] != "Default":
                ns.SetNetclassPatternAssignment(net, info["class"])
        # drill/place (aux) origin at the outline's bottom-left: gerbers, drill and CPL all use it,
        # so JLC sees matching coordinates and CPL positions are positive
        xs = [x for x, _ in j["geometry"]["outline"]]
        ys = [y for _, y in j["geometry"]["outline"]]
        ds.SetAuxOrigin(self.pt(min(xs), max(ys)))
        ds.SetGridOrigin(self.pt(0, 0))

        for name in j["nets"]:
            n = pcbnew.NETINFO_ITEM(b, name)
            b.Add(n)
            self.nets[name] = n

    @staticmethod
    def _apply_class(nc, c):
        nc.SetTrackWidth(mm(c["track_width"]))
        nc.SetClearance(mm(c["clearance"]))
        nc.SetViaDiameter(mm(c.get("via_diameter", 0.6)))
        nc.SetViaDrill(mm(c.get("via_drill", 0.3)))

    # -- mechanical ----------------------------------------------------------
    def poly_edge(self, pts, layer=pcbnew.Edge_Cuts, width=0.05):
        s = pcbnew.PCB_SHAPE(self.board)
        s.SetShape(pcbnew.SHAPE_T_POLY)
        s.SetFilled(False)
        s.SetLayer(layer)
        s.SetWidth(mm(width))
        s.SetPolyPoints([self.pt(x, y) for x, y in pts])
        self.board.Add(s)

    def outline(self):
        g = self.job["geometry"]
        self.poly_edge(g["outline"])
        for c in g.get("cutouts", []):
            self.poly_edge(c)
        for k in g.get("keepouts", []):
            z = pcbnew.ZONE(self.board)
            z.SetIsRuleArea(True)
            lyr = pcbnew.LSET()
            for name in k.get("layers", ["F.Cu", "B.Cu"]):
                lyr.AddLayer(LAYER[name])
            z.SetLayerSet(lyr)
            no = set(k.get("no", ["tracks", "vias", "copper"]))
            z.SetDoNotAllowTracks("tracks" in no)
            z.SetDoNotAllowVias("vias" in no)
            z.SetDoNotAllowZoneFills("copper" in no)
            z.SetDoNotAllowPads("pads" in no)
            z.SetDoNotAllowFootprints("parts" in no)
            z.SetZoneName(k.get("name", "keepout"))
            z.Outline().NewOutline()
            for x, y in k["polygon"]:
                z.Outline().Append(self.pt(x, y))
            self.board.Add(z)

    # -- footprints ----------------------------------------------------------
    def footprints(self):
        place = self.job["placement"]
        for p in self.job["parts"]:
            lib, name = p["footprint"].split(":", 1)
            path = p.get("footprint_path") or os.path.join(STOCK_FP, lib + ".pretty")
            fp = pcbnew.FootprintLoad(path, name)
            if fp is None:
                raise SystemExit(f"footprint not found: {p['footprint']} ({path})")
            fp.SetReference(p["ref"])
            fp.SetValue(p["value"])
            fp.SetFPID(pcbnew.LIB_ID(lib, name))
            for k, v in (("LCSC", p.get("lcsc")), ("MPN", p.get("mpn"))):
                if v:
                    fp.SetField(k, v)
                    fp.GetField(k).SetVisible(False)
            ref = fp.Reference()
            ref.SetVisible(self.job.get("silk_refs", True))
            ref.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
            ref.SetTextThickness(mm(0.15))
            model = p.get("meta", {}).get("model")
            if model:
                m = pcbnew.FP_3DMODEL()
                m.m_Filename = model["path_win"]
                m.m_Offset = pcbnew.VECTOR3D(*model.get("offset", [0, 0, 0]))
                m.m_Rotation = pcbnew.VECTOR3D(*model.get("rotate", [0, 0, 0]))
                fp.Models().clear()
                fp.Models().push_back(m)
            if p.get("dnp"):
                fp.SetDNP(True)
                fp.SetExcludedFromBOM(True)
                fp.SetExcludedFromPosFiles(True)
            conn = p.get("meta", {}).get("zone_connection", {})
            modes = {"full": pcbnew.ZONE_CONNECTION_FULL, "thermal": pcbnew.ZONE_CONNECTION_THERMAL,
                     "none": pcbnew.ZONE_CONNECTION_NONE}
            for pad in fp.Pads():
                net = p["pad_nets"].get(pad.GetNumber())
                if net:
                    pad.SetNet(self.nets[net])
                if pad.GetNumber() in conn:
                    pad.SetLocalZoneConnection(modes[conn[pad.GetNumber()]])
            self.board.Add(fp)
            spot = place.get(p["ref"])
            if spot is None:
                self.report["warnings"].append(f"{p['ref']} has no placement; left at origin")
                spot = {"at": [0, 0]}
            fp.SetPosition(self.pt(*spot["at"]))
            if spot.get("side", "top") == "bottom":
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetOrientationDegrees(float(spot.get("rot", 0)))
            self.report["placed"].append(p["ref"])

    # -- copper --------------------------------------------------------------
    def tracks(self):
        for t in self.job.get("tracks", []):
            pts = t["points"]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                tr = pcbnew.PCB_TRACK(self.board)
                tr.SetStart(self.pt(x1, y1))
                tr.SetEnd(self.pt(x2, y2))
                tr.SetWidth(mm(t["width"]))
                tr.SetLayer(LAYER[t["layer"]])
                tr.SetNet(self.nets[t["net"]])
                self.board.Add(tr)
        for v in self.job.get("vias", []):
            via = pcbnew.PCB_VIA(self.board)
            via.SetPosition(self.pt(*v["at"]))
            via.SetWidth(mm(v.get("diameter", 0.6)))
            via.SetDrill(mm(v.get("drill", 0.3)))
            via.SetNet(self.nets[v["net"]])
            self.board.Add(via)

    def zones(self):
        g = self.job["geometry"]
        for zd in self.job.get("zones", []):
            poly = g["outline"] if zd.get("outline", "board") == "board" else zd["outline"]
            z = pcbnew.ZONE(self.board)
            z.SetLayer(LAYER[zd["layer"]])
            z.SetNet(self.nets[zd["net"]])
            z.SetLocalClearance(mm(zd.get("clearance", 0.3)))
            z.SetMinThickness(mm(zd.get("min_width", 0.25)))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)  # SMD pads solid, THT relieved
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            z.SetThermalReliefGap(mm(zd.get("thermal_gap", 0.3)))
            z.SetThermalReliefSpokeWidth(mm(zd.get("spoke_width", 0.4)))
            z.SetAssignedPriority(zd.get("priority", 0))
            z.Outline().NewOutline()
            for x, y in poly:
                z.Outline().Append(self.pt(x, y))
            self.board.Add(z)

    def run(self):
        self.setup()
        self.outline()
        self.footprints()
        self.tracks()
        self.zones()
        pcbnew.ZONE_FILLER(self.board).Fill(self.board.Zones())
        pcbnew.SaveBoard(self.job["board_path"], self.board)
        return self.report


if __name__ == "__main__":
    job = json.load(open(sys.argv[1], encoding="utf-8"))
    rep = Builder(job).run()
    json.dump(rep, open(job["report_path"], "w", encoding="utf-8", newline="\n"), indent=1)
    print(f"board written: {job['board_path']} ({len(rep['placed'])} parts, {len(rep['warnings'])} warnings)")
