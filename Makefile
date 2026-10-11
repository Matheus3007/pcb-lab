# Single entry point. Usage: make <target> BOARD=<name>
# Stage details: docs/pipeline.md
SHELL := /bin/bash
BOARD ?=
REF ?= HEAD
GATE ?= 1
PCBKIT = . toolchain/env.sh && cd tools && python -m pcbkit

.PHONY: help toolchain build check render render-fast diff fab report gate parts all _need_board

help:
	@echo "make {all|build|check|render|render-fast|fab|diff|gate|parts|report} BOARD=<name> [REF=<git ref>] [GATE=1|2|3]"
	@echo "make toolchain   # one-time setup (see toolchain/README.md)"
	@ls boards | grep -v -e '^_' -e README || echo '(no boards yet)'

_need_board:
	@test -n "$(BOARD)" || (echo "BOARD=<name> required"; exit 2)
	@test -d "boards/$(BOARD)" || (echo "no such board: boards/$(BOARD)"; exit 2)

toolchain:
	toolchain/setup.sh

all: _need_board          ## build -> render -> check (+ dashboard). The iteration command.
	@$(PCBKIT) all $(BOARD)

build: _need_board        ## circuit -> outline -> place -> route -> stitch -> board.json
	@$(PCBKIT) build $(BOARD)

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

report: _need_board       ## regenerate the review dashboard only
	@$(PCBKIT) report $(BOARD)
