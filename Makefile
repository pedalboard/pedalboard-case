.PHONY: help all

.DEFAULT_GOAL := help

DISPLAY_WRAPPER ?= xvfb-run -a

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

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

