# Top panel outputs — all derived from pedalboard-display KiCad PCB
#
# Usage:
#   make panel          — regenerate all panel outputs
#   make coords         — extract positions from KiCad PCB
#   make gcode          — generate G-code (default: 4mm tool)
#   make dxf            — generate DXF for CNC shop
#   make template       — generate printable SVG/PDF template

DISPLAY_PCB := ../../pedalboard-display/pedalboard-display.kicad_pcb
COORDS := top-panel-coords.json

.PHONY: panel coords gcode dxf template clean

panel: coords gcode dxf template ## generate all panel outputs

coords: $(COORDS) ## extract positions from KiCad PCB

$(COORDS): $(DISPLAY_PCB) extract-coords.py
	python3 extract-coords.py --pcb $(DISPLAY_PCB) --output $(COORDS)

gcode: $(COORDS) ## generate G-code
	python3 top-panel-gcode.py > ../generated/top-panel.nc

dxf: $(COORDS) ## generate DXF for CNC shop
	python3 top-panel-dxf.py --output ../generated/top-panel.dxf

template: $(COORDS) ## generate printable SVG/PDF cutting template
	python3 top-panel-template.py --output ../generated/display-cutout-template.svg
	rsvg-convert -f pdf ../generated/display-cutout-template.svg -o ../generated/display-cutout-template.pdf

clean: ## remove generated panel files
	rm -f $(COORDS)
	rm -f ../generated/top-panel.nc
	rm -f ../generated/top-panel.dxf
