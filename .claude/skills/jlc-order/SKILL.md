---
name: jlc-order
description: Prepare a pcb-lab board for a JLCPCB PCB + assembly order. Final checks, fab outputs (gerbers zip, BOM, CPL), the gate-3 packet, the human's upload checklist (rotation verification in JLC's preview), and tagging the release. Use when a board is routed and passing and the user wants to order or get fab files.
---

# Prepare a JLC order

Ordering is the human's action (payment). You prepare everything and hand over a checklist.

## 1. Final state
```bash
make parts BOARD=<name> REFRESH=1     # stock and prices as of today
make all BOARD=<name>                 # must PASS; every waiver has a reason
make fab BOARD=<name>
make gate BOARD=<name> GATE=3
```
Re-read `docs/jlcpcb.md` against JLC's live capabilities pages if it's older than ~3 months
(they change); update the doc and `toolchain/rules/jlc.yaml` if needed, then re-run.

## 2. Files (boards/<name>/build/fab/)
- `<name>-gerbers.zip`: upload under "Add gerber file".
- `<name>-bom.csv`: Comment, Designator, Footprint, LCSC Part #.
- `<name>-cpl.csv`: Designator, Mid X, Mid Y, Layer, Rotation (rotation-corrected).
- `cpl_corrections.json`: which parts got a correction, from which `lib/jlc_rotations.csv` rule.

## 3. Order settings to tell the human
From board.yaml/spec: layers, thickness, quantity, surface finish, color, assembly tier
(Economic/Standard), assembly side, "confirm parts placement: yes". For Standard + small boards, the
panel with rails/fiducials (not yet automated: flag it as a blocker).

## 4. The human's checklist (put it in your reply)
1. Upload the zip → check JLC's Gerber viewer: outline, cutouts/slots, drill hits, silkscreen.
2. Enable assembly → upload BOM + CPL → check every part matched the intended LCSC ID.
3. **Placement preview: check each part's rotation and polarity** (pin 1 dots, LED cathode, diode
   bands, connector mouths facing out). The CPL corrections are community hints, not verified.
4. Any wrong rotation: tell me ref + the correct angle → I add a confirmed rule at the TOP of
   `lib/jlc_rotations.csv`, regenerate, and they re-upload.
5. Note the order number.

## 5. After the order
- Record in `spec.md` changelog: date, order number, quantity, tier, confirmed rotation fixes.
- `git tag <name>/vX.Y -m "JLC order <number>"` and commit. Fab files are reproducible from the tag;
  keep the zip/CSVs the human uploaded too (e.g. attach them to a GitHub release).
- Any rotation confirmed correct or fixed: mark it confirmed in `lib/jlc_rotations.csv` (comment with date and board).
