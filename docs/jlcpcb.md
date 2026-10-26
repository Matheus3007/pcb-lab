# JLCPCB fab and assembly limits

Source: jlcpcb.com/capabilities/pcb-capabilities and /pcb-assembly-capabilities, read
2026-10-11. **Re-check before each order**, since JLC changes these. Our design rules use
the *recommended* value where one is given, not the absolute minimum, unless the board spec
explicitly allows it.

## PCB (rigid FR-4)

| Rule | JLC minimum | **Our default** |
|---|---|---|
| Trace / space, 1 oz, 1–2 layer | 0.10 / 0.10 mm | 0.15 / 0.15 mm |
| Trace / space, 1 oz, multilayer | 0.09 / 0.09 mm | 0.125 / 0.125 mm |
| Trace / space, 2 oz, 2-layer | 0.16 / 0.16 mm | 0.20 / 0.20 mm |
| Trace / space, 2 oz, multilayer | 0.15 / 0.15 mm | 0.20 / 0.20 mm |
| Via hole / pad | 0.15 / 0.25 mm (0.10/0.20 only if ≤1 mm thick + ENIG/OSP); pad ≥ hole + 0.10 (0.15 preferred) | 0.30 / 0.55 mm (0.30/0.45 when dense, see below) |
| Via hole to track, inner-layer via hole to copper | 0.20 mm (checked 2026-10-25) | 0.25 mm (`hole_clearance`) |
| Min PTH drill (2+ layer) | 0.15 mm | 0.30 mm |
| Min NPTH hole | 0.50 mm | 0.50 mm |
| Hole-to-hole spacing | vias 0.20 mm, pad holes 0.45 mm (checked 2026-10-11) | 0.50 mm (boards may set vias-only 0.30 with a reason) |
| PTH annular ring, 1 oz | 2-layer 0.18 (rec. 0.25); multilayer 0.15 (rec. 0.20) | recommended values |
| Copper to routed edge | 0.20 mm | 0.30 mm |
| Copper to V-cut edge | 0.40 mm | 0.50 mm |
| Plated slot min width | 0.5 mm (2-layer), 0.35 mm (multilayer); length ≥ 2×width | same |
| Non-plated slot min width | 1.0 mm | 1.0 mm (cutouts: ≥ 1.0 mm internal radius assumed from router bit) |
| Silkscreen line / text height | 0.15 mm / 1.0 mm | same |
| Pad-to-silk clearance | 0.15 mm | same |
| Solder mask bridge, 1 oz | 0.10 mm (0.13 black/white) | same |
| Board thickness (FR-4) | 0.4, 0.6, 0.8, 1.0, 1.2, 1.6, 2.0 mm | per spec |
| Min board size | 3×3 mm (10×10 castellated) | n/a |

**Via drill below 0.3 mm costs extra** (live quote 2026-10-25, 4-layer, 5 boards): the "0.2mm/(0.3/0.35mm)" via option
+$17, and it makes JLC add a 4-wire Kelvin test (+$17) and TG155 (+$7.5) by itself. Prefer 0.3 / 0.45 mm vias on dense
boards (JLC's own "0.3mm/(0.4/0.45mm)" option): set `min_annular_ring: 0.075` and `hole_clearance: 0.2` in board.yaml.
ENIG and non-green mask also disable Economic PCBA.

Blind/buried/HDI vias and via-in-pad exist but cost more. **Through-hole vias only unless the
board spec says otherwise.** Impedance control: 4+ layers, ±10%.

## Assembly (PCBA)

| | Economic | Standard |
|---|---|---|
| Single PCB size | 10×10 to 470×500 mm | **70×70** to 460×500 mm |
| Panel size | 10×10 to 250×250 mm | 70×70 to 250×250 mm |
| Sides | **one side only** | one or both |
| Layers | 2, 4, 6 | 1–32 |
| Thickness | 0.8–1.6 mm | any |
| Castellated / edge plating | no | yes |
| Min package | **0402** | 0201 |
| Min IC pitch | 0.40 mm | 0.35 mm |
| Min BGA pitch | 0.5 mm | 0.3 mm |
| Edge rails + fiducials | not needed | **required** |
| Quantity | 2–50 | 2–80,000 |

### What this means for small boards
- A board smaller than 70×70 mm that needs **two-sided assembly** (or 0201, or <0.8 mm
  thickness, or a "Standard only" part) must go Standard. **JLC adds the rails itself** (order option
  "Edge Rails/Fiducials: Added by JLCPCB", default; checked 2026-10-25): it treats each board as 71×71 mm, no
  panel fee, so no panelizer is needed for small quantities.
- Some parts are **"Standard Only"** (JLC catalog `componentProductType` = 2), e.g. the LSM6DSV32X (C22461202):
  one such part forces Standard PCBA (setup fee + per-BOM-line feeder fee, ~$1.55 per line in 2026-10).
- Economic + single-sided is the cheapest/simplest path; prefer it unless the size
  budget forces both sides.
- Assembled boards ship with rails attached unless depanelization is ordered.

## Parts
- **Basic** parts: preloaded on the pick-and-place machines, no setup fee. **Preferred Extended**: small/no fee
  (check current price guide). **Extended**: per-unique-part setup fee. Minimize unique
  Extended parts.
- Check stock at order time; pinning an LCSC ID doesn't reserve stock.

## CPL / BOM format
- BOM columns: `Comment, Designator, Footprint, LCSC Part #`.
- CPL columns: `Designator, Mid X, Mid Y, Layer, Rotation`.
- Rotation/origin differences between KiCad footprints and JLC's library are the #1
  assembly error. The pipeline applies per-package corrections; the human confirms in
  JLC's placement preview at gate 3.
