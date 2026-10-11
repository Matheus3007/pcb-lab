# Single entry point. Usage: make <target> BOARD=<name>
# Target contract and implementation status: docs/pipeline.md
BOARD ?=
B := boards/$(BOARD)

.PHONY: help toolchain build check render diff fab all _need_board

help:
	@echo "make {build|check|render|diff|fab|all} BOARD=<name>   (see docs/pipeline.md)"
	@ls boards | grep -v -e '^_' -e README || echo '(no boards yet)'

_need_board:
	@test -n "$(BOARD)" || (echo "BOARD=<name> required"; exit 2)
	@test -d "$(B)" || (echo "no such board: $(B)"; exit 2)

# Stubs until Phase 0 implements them: fail loudly instead of pretending to work.
build check render diff fab: _need_board
	@echo "make $@: not implemented yet (Phase 0, see docs/pipeline.md)"; exit 3

all: build check render

toolchain:
	@echo "make toolchain: not implemented yet (Phase 0, see docs/pipeline.md)"; exit 3
