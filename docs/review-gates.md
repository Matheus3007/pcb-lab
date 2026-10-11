# Review gates (human sign-off)

The human reviews results, not code. At each gate the agent produces a short review packet
(`boards/<name>/build/review/gate-N.md` + the images it references) and **stops** until
the human approves. Record the approval in the board's `spec.md` changelog (date, gate, notes).

These three are cheap for the human to check and expensive to get wrong, since a wrong pinout passes every
automated check.

## Gate 1: Parts and pinouts (after circuit, before placement)
Packet contains:
- BOM table: ref, value, package, LCSC ID, Basic/Preferred/Extended, stock, unit price.
- The generated schematic (`renders/schematic.png`) and a pin table per part: pad, KiCad symbol pin
  name, our name, electrical type, net. Read it next to the datasheet. Layout changes for readability
  are welcome (`make sch-open`); they can't change connectivity.
- For each IC/connector: datasheet link, the pin mapping used, and whether the agent
  verified it against the datasheet (yes / partially / no + why).
- Power tree: rails, sources, max currents, regulator dissipation estimates.
- Anything the agent was unsure about, listed first.

## Gate 2: Placement (before routing)
Packet contains:
- Top + bottom placement renders with the outline/chassis overlay and keepouts.
- 3D render(s); mechanical interference result if chassis CAD exists.
- Placement rationale for anchored/critical parts (connectors, IMU, power stage, sense resistors).
- Check results that already apply (edge clearance, height zones, decoupling distance).

## Gate 3: Pre-order
Packet contains:
- `make check` summary: all green, waivers listed with reasons.
- Copper layer renders + 3D top/bottom.
- Final BOM + CPL, Extended part count, estimated cost.
- Reminder for the human to upload to JLC and confirm the **online Gerber viewer and
  component placement preview** (rotations!) before paying.
- After ordering: tag `<board>/vX.Y` and record the order number in `spec.md`.
