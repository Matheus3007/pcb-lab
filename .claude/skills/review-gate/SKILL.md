---
name: review-gate
description: Produce a pcb-lab review packet for gate 1 (parts/pinouts), gate 2 (placement) or gate 3 (pre-order), present it to the human, and stop until they approve. Use at each gate in docs/review-gates.md, or when the user asks to review a board.
---

# Review gate

The human reviews **results, not code**, and never opens KiCad. Make the packet self-explanatory.

## 1. Make sure the board is in a reviewable state
```bash
make all BOARD=<name>          # must say "checks PASS" (or every open item explained)
make fab BOARD=<name>          # gate 3 only
make gate BOARD=<name> GATE=<n>
```
Output: `boards/<name>/build/review/gate-<n>.md` (images are linked from `../renders/`).

## 2. Check the packet yourself before handing it over
- **Gate 1**: every IC/connector has `pinout_source` + date; you actually looked at the datasheet page
  PNG; required external parts from the datasheet are present; assertions cover the risky numbers
  (abs-max voltages, regulator dissipation, LED current, divider ratios); Extended-part count is justified.
- **Gate 2**: open `placement.png`, `3d_iso.png`, `3d_top.png`, `3d_bottom.png` and confirm connectors face out,
  heights fit the envelope, decoupling sits at its pins, sensors are where the spec says (e.g. IMU near
  the centre of rotation), nothing sits on high-shock edges, and the assembly tier is respected.
- **Gate 3**: everything green; the CPL corrections list is in the packet; the cost estimate is sane.

## 3. Present it
Reply with a short summary: the gate, PASS/FAIL, a **numbered list of things you want the human to
decide or look at first** (uncertainties, judgement calls), and the paths:
the packet file and the dashboard (`build/review/index.html`, VS Code Live Preview).
Then **stop**. Don't start the next stage in the same turn.

## 4. Record the outcome
When the human approves (or asks for changes), add a row to the board's `spec.md` changelog:
`| YYYY-MM-DD | gate N approved/changes | their notes |`, and commit
(`<board>: gate N approved`). Changes requested → `/board-iteration`, then regenerate the packet.
