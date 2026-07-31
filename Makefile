.PHONY: help all

.DEFAULT_GOAL := help

# on CI DISPLAY_WRAPPER ?= xvfb-run -a
DISPLAY_WRAPPER ?=

GEN     := ./generated
SRC     := ./parts
SRCS    := $(wildcard $(SRC)/*.scad)
STLS    := $(patsubst $(SRC)/%.scad,$(GEN)/%.stl,$(SRCS))
PNGS    := $(patsubst $(SRC)/%.scad,$(GEN)/%.png,$(SRCS))

all: $(STLS) $(PNGS) ## generate all parts

$(GEN)/%.stl: $(SRC)/%.scad | $(GEN)
	openscad -o $@ $<

$(GEN)/%.png: $(SRC)/%.scad | $(GEN)
	$(DISPLAY_WRAPPER) openscad -o $@ --autocenter --viewall --colorscheme=Nature --imgsize=1200,800 $<

clean:
	rm -f $(STLS)
	rm -f $(PNGS)

test: ## Validate generated G-code for grblHAL compatibility
	@echo "Testing G-code generation (center origin, angle=0)..."
	@python3 parts/top-panel-gcode.py --origin center --angle 0 > /dev/null
	@echo "Testing G-code generation (center origin, angle=0.5)..."
	@python3 parts/top-panel-gcode.py --origin center --angle 0.5 > /dev/null
	@echo "Testing G-code generation (corner origin)..."
	@python3 parts/top-panel-gcode.py --origin corner > /dev/null
	@echo "All G-code validation passed."

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

