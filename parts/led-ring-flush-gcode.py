#!/usr/bin/env python3
"""
Generate G-code for cutting plexiglass LED ring (flush mount design).

Part: stepped ring — ø24mm top × 1mm, ø22mm bottom × 1mm, ø14mm center hole.
Material: 2mm plexiglass sheet
Tool: 4mm single flute downcut endmill

Origin: center of part, Z0 = top of plexiglass surface.
Fixture: double-sided tape on sacrificial board.

Usage:
    python3 led-ring-flush-gcode.py > led-ring-flush.nc
"""

import math

# === PARAMETERS ===

tool_dia = 4.0          # mm
tool_r = tool_dia / 2.0

# Part dimensions
plexi_od = 24.0         # mm — outer diameter (top lip)
plexi_step_od = 22.0    # mm — bottom step diameter (through-cut)
center_hole_d = 14.0    # mm — center hole for actuator
plexi_thickness = 2.0   # mm — total material thickness
step_depth = 1.0        # mm — lip is 1mm thick (top half only)

# Cutting parameters
feed_xy = 500           # mm/min — plexiglass, conservative
feed_z = 100            # mm/min — plunge
spindle_rpm = 15000     # dial 3 on Makita
safe_z = 15.0           # mm — safe retract height
depth_per_pass = 0.5    # mm — 0.5mm per pass (4 passes for through, quality over speed)
extra_depth = 0.3       # mm — cut slightly past material for clean through

# === G-CODE GENERATION ===

lines = []

def emit(line=""):
    lines.append(line)

def circle(cx, cy, radius, z):
    """Cut a full circle at given Z depth."""
    # Start at 3 o'clock position
    start_x = cx + radius
    start_y = cy
    emit(f"G0 X{start_x:.3f} Y{start_y:.3f}")
    emit(f"G1 Z{z:.3f} F{feed_z}")
    emit(f"G2 X{start_x:.3f} Y{start_y:.3f} I{-radius:.3f} J0 F{feed_xy}")

# Header
emit("(LED ring flush mount — plexiglass)")
emit(f"(Tool: {tool_dia}mm single flute downcut)")
emit(f"(Material: {plexi_thickness}mm plexiglass)")
emit(f"(Part: OD {plexi_od}mm lip, OD {plexi_step_od}mm through, ID {center_hole_d}mm)")
emit(f"(Feed: {feed_xy}mm/min XY, {feed_z}mm/min Z)")
emit()
emit("G21")
emit("G90")
emit("G17")
emit()
emit(f"M3 S{spindle_rpm}")
emit("G4 P2")
emit()

# Safety: start from center at safe Z
emit(f"G0 Z{safe_z}")
emit("G0 X0 Y0")
emit()

# === 1. Center hole (ø14mm, full depth) ===
emit("(=== CENTER HOLE ===)")
center_r = (center_hole_d - tool_dia) / 2.0  # toolpath radius = 5mm
total_depth = plexi_thickness + extra_depth

emit(f"G0 Z{safe_z}")
z = 0
while z > -total_depth:
    z = max(z - depth_per_pass, -total_depth)
    circle(0, 0, center_r, z)
# Spring pass
emit(f"G2 X{center_r:.3f} Y0 I{-center_r:.3f} J0 F{feed_xy}")
emit(f"G0 Z{safe_z}")
emit()

# === 2. Outer lip cut (ø24mm, 1mm deep from top) ===
# This creates the step — cuts the top 1mm at the larger diameter
emit("(=== OUTER LIP — 1mm deep at ø24mm ===)")
lip_r = (plexi_od - tool_dia) / 2.0  # toolpath radius = 10mm

emit(f"G0 Z{safe_z}")
circle(0, 0, lip_r, -step_depth)
# Spring pass
emit(f"G2 X{lip_r:.3f} Y0 I{-lip_r:.3f} J0 F{feed_xy}")
emit(f"G0 Z{safe_z}")
emit()

# === 3. Through cut (ø22mm, full depth) ===
# This separates the part from the sheet
emit("(=== THROUGH CUT — ø22mm full depth ===)")
through_r = (plexi_step_od - tool_dia) / 2.0  # toolpath radius = 9mm

emit(f"G0 Z{safe_z}")
z = 0
while z > -total_depth:
    z = max(z - depth_per_pass, -total_depth)
    circle(0, 0, through_r, z)
# Spring pass
emit(f"G2 X{through_r:.3f} Y0 I{-through_r:.3f} J0 F{feed_xy}")
emit(f"G0 Z{safe_z}")
emit()

# Footer
emit("M5")
emit("G0 X0 Y0")
emit("M2")

print("\n".join(lines))
