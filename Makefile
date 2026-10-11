# Single entry point. Usage: make <target> BOARD=<name>
# Stage details: docs/pipeline.md
SHELL := /bin/bash
BOARD ?=
REF ?= HEAD
GATE ?= 1
PCBKIT = . toolchain/env.sh && cd tools && python -m pcbkit

.PHONY: sch sch-open open part footprint help toolchain build check render render-fast diff fab report gate parts all _need_board

help:
	@echo "make {all|build|check|render|render-fast|fab|diff|gate|parts|report} BOARD=<name> [REF=<git ref>] [GATE=1|2|3]"
	@echo "make open BOARD=<name>   # view the board in KiCad's PCB editor"
	@echo "make sch BOARD=<name> | make sch-open BOARD=<name>   # generated schematic; edit its layout in KiCad"
	@echo "make part LCSC=<C...> | make footprint FP=<Lib:Name>   # part research"
	@echo "make toolchain   # one-time setup (see toolchain/README.md)"
	@ls boards | grep -v -e '^_' -e README || echo '(no boards yet)'

_need_board:
	@test -n "$(BOARD)" || (echo "BOARD=<name> required"; exit 2)
	@test -d "boards/$(BOARD)" || (echo "no such board: boards/$(BOARD)"; exit 2)

toolchain:
	toolchain/setup.sh

all: _need_board          ## build -> render -> check (+ dashboard). The iteration command.
	@$(PCBKIT) all $(BOARD) $(if $(REROUTE),--reroute,)

build: _need_board        ## circuit -> outline -> place -> route -> stitch -> board.json
	@$(PCBKIT) build $(BOARD) $(if $(REROUTE),--reroute,)

sch: _need_board          ## circuit -> schematic (+ ERC, pin table, schematic.png) only; no board needed
	@$(PCBKIT) sch $(BOARD)

sch-open: _need_board     ## edit the schematic LAYOUT in KiCad; save, then `make sch` imports it into schematic.yaml
	@test -f boards/$(BOARD)/build/work/$(BOARD).kicad_sch || (echo "generate first: make sch BOARD=$(BOARD)"; exit 2)
	@("/mnt/c/Program Files/KiCad/10.0/bin/eeschema.exe" "$$(wslpath -w boards/$(BOARD)/build/work/$(BOARD).kicad_sch)" >/dev/null 2>&1 &)
	@echo "opening the schematic in KiCad: move symbols/labels, draw wires or notes, SAVE, then run make sch BOARD=$(BOARD)"
	@echo "(connectivity stays in circuit.py: wires/labels that contradict it are dropped and reported)"

render: _need_board       ## 2D + 3D renders -> build/renders/
	@$(PCBKIT) render $(BOARD)

render-fast: _need_board  ## 2D renders only
	@$(PCBKIT) render $(BOARD) --fast

check: _need_board        ## all checks -> build/reports/summary.md; non-zero exit on failure
	@$(PCBKIT) check $(BOARD)

fab: _need_board          ## JLC gerbers zip + BOM + CPL -> build/fab/
	@$(PCBKIT) fab $(BOARD)

diff: _need_board         ## semantic + visual diff vs REF (default HEAD)
	@$(PCBKIT) diff $(BOARD) --ref $(REF)

gate: _need_board         ## review packet for GATE=1|2|3 -> build/review/gate-N.md
	@$(PCBKIT) gate $(BOARD) --gate $(GATE)

parts: _need_board        ## JLC tier/stock/price for every part (add REFRESH=1 to re-query)
	@$(PCBKIT) parts $(BOARD) $(if $(REFRESH),--refresh,)

open: _need_board         ## view the generated board in KiCad's PCB editor (read-only use: edits are overwritten by the next build)
	@test -f boards/$(BOARD)/build/work/$(BOARD).kicad_pcb || (echo "build first: make build BOARD=$(BOARD)"; exit 2)
	@rm -f boards/$(BOARD)/build/work/$(BOARD).kicad_prl
	@("/mnt/c/Program Files/KiCad/10.0/bin/pcbnew.exe" "$$(wslpath -w boards/$(BOARD)/build/work/$(BOARD).kicad_pcb)" >/dev/null 2>&1 &)
	@echo "opening boards/$(BOARD)/build/work/$(BOARD).kicad_pcb in KiCad (look, don't edit: change the source and rebuild)"

part:                     ## research a part: make part LCSC=C5446 (JLC data, datasheet pin pages, footprint candidates)
	@test -n "$(LCSC)" || (echo "LCSC=<C-number> required"; exit 2)
	@$(PCBKIT) part $(LCSC)

footprint:                ## inspect a footprint: make footprint FP=Package_TO_SOT_SMD:SOT-23-3 (pads, facing, 3D model, PNG)
	@test -n "$(FP)" || (echo "FP=<Lib:Name> required"; exit 2)
	@$(PCBKIT) footprint "$(FP)"

report: _need_board       ## regenerate the review dashboard only
	@$(PCBKIT) report $(BOARD)
