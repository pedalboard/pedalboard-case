#!/usr/bin/env python3
"""
Generate G-code for cutting plexiglass display window (flush mount).

Part: stepped rectangle — 36.5×38.7mm top × 1mm, 34.1×36.3mm bottom × 1mm.
Material: 2mm plexiglass sheet
Tool: 4mm single flute downcut endmill
Corner radius: 2mm (matches tool radius)

Origin: center of part, Z0 = top of plexiglass surface.
Fixture: double-sided tape on sacrificial board.

Usage:
    python3 display-window-flush-gcode.py > display-window-flush.nc
"""

import math

# === PARAMETERS ===

tool_dia = 4.0
tool_r = tool_dia / 2.0

# Part dimensions (match top-panel-gcode.py display cutout/recess)
top_w = 44.5            # mm — recess width (fills recess)
top_h = 38.7            # mm — recess height
step_w = 42.1           # mm — through-cut width - 0.4mm clearance
step_h = 36.3           # mm — through-cut height - 0.4mm clearance
plexi_thickness = 2.0   # mm
step_depth = 1.0        # mm — lip is top 1mm

# Cutting parameters
feed_xy = 500           # mm/min
feed_z = 100            # mm/min
spindle_rpm = 15000
safe_z = 15.0           # mm
depth_per_pass = 0.5    # mm — quality over speed
extra_depth = 0.3       # mm

# === G-CODE GENERATION ===

lines = []

def emit(line=""):
    lines.append(line)

def rect_contour(cx, cy, width, height, z):
    """Cut a rectangular contour with corner radius = tool_r at given Z."""
    hw = width / 2.0 - tool_r
    hh = height / 2.0 - tool_r

    # Start at mid-point of bottom edge
    start_x = cx
    start_y = cy - hh
    emit(f"G0 X{start_x:.3f} Y{start_y:.3f}")
    emit(f"G1 Z{z:.3f} F{feed_z}")

    # Rectangle CCW
    emit(f"G1 X{cx + hw:.3f} Y{cy - hh:.3f} F{feed_xy}")
    emit(f"G1 X{cx + hw:.3f} Y{cy + hh:.3f}")
    emit(f"G1 X{cx - hw:.3f} Y{cy + hh:.3f}")
    emit(f"G1 X{cx - hw:.3f} Y{cy - hh:.3f}")
    emit(f"G1 X{cx:.3f} Y{cy - hh:.3f}")


# Header
emit("(Display window flush mount — plexiglass)")
emit(f"(Tool: {tool_dia}mm single flute downcut)")
emit(f"(Material: {plexi_thickness}mm plexiglass)")
emit(f"(Part: {top_w}×{top_h}mm lip, {step_w}×{step_h}mm through, 2mm corner radius)")
emit(f"(Feed: {feed_xy}mm/min XY, {feed_z}mm/min Z)")
emit()
emit("G21")
emit("G90")
emit("G17")
emit()
emit(f"M3 S{spindle_rpm}")
emit("G4 P2")
emit()
emit(f"G0 Z{safe_z}")
emit("G0 X0 Y0")
emit()

# === 1. Outer lip cut (top_w × top_h, 1mm deep) ===
# Creates the step — cuts the top 1mm at the larger dimension
emit("(=== OUTER LIP — 1mm deep ===)")
emit(f"G0 Z{safe_z}")

n_passes_lip = math.ceil(step_depth / depth_per_pass)
z = 0
for i in range(n_passes_lip):
    z = max(z - depth_per_pass, -step_depth)
    rect_contour(0, 0, top_w, top_h, z)

# Spring pass
hw = top_w / 2.0 - tool_r
hh = top_h / 2.0 - tool_r
emit(f"G1 X{hw:.3f} Y{-hh:.3f} F{feed_xy}")
emit(f"G1 X{hw:.3f} Y{hh:.3f}")
emit(f"G1 X{-hw:.3f} Y{hh:.3f}")
emit(f"G1 X{-hw:.3f} Y{-hh:.3f}")
emit(f"G1 X0 Y{-hh:.3f}")
emit(f"G0 Z{safe_z}")
emit()

# === 2. Through cut (step_w × step_h, full depth) ===
# Separates the part from the sheet
emit("(=== THROUGH CUT ===)")
emit(f"G0 Z{safe_z}")

total_depth = plexi_thickness + extra_depth
n_passes_through = math.ceil(total_depth / depth_per_pass)
z = 0
for i in range(n_passes_through):
    z = max(z - depth_per_pass, -total_depth)
    rect_contour(0, 0, step_w, step_h, z)

# Spring pass
hw = step_w / 2.0 - tool_r
hh = step_h / 2.0 - tool_r
emit(f"G1 X{hw:.3f} Y{-hh:.3f} F{feed_xy}")
emit(f"G1 X{hw:.3f} Y{hh:.3f}")
emit(f"G1 X{-hw:.3f} Y{hh:.3f}")
emit(f"G1 X{-hw:.3f} Y{-hh:.3f}")
emit(f"G1 X0 Y{-hh:.3f}")
emit(f"G0 Z{safe_z}")
emit()

# Footer
emit("M5")
emit("G0 X0 Y0")
emit("M2")

print("\n".join(lines))
