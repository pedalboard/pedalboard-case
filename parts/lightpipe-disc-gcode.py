#!/usr/bin/env python3
"""
Generate G-code for cutting plexiglass light pipe discs (ø6mm × 2mm).

Simple circular contour cut from 2mm plexiglass sheet.
Tool: 4mm single flute downcut endmill.
Origin: center of disc, Z0 = top of plexiglass.

Usage:
    python3 lightpipe-disc-gcode.py > lightpipe-disc.nc
    python3 lightpipe-disc-gcode.py --count 4 > lightpipe-disc.nc
"""

import argparse
import math

# === PARAMETERS ===

disc_d = 6.0            # mm
plexi_thickness = 2.0   # mm
tool_dia = 4.0          # mm
tool_r = tool_dia / 2.0

feed_xy = 500           # mm/min
feed_z = 100            # mm/min
spindle_rpm = 15000
safe_z = 15.0           # mm
depth_per_pass = 0.5    # mm
extra_depth = 0.3       # mm

# Spacing between discs when cutting multiple
disc_spacing = 10.0     # mm center-to-center


def parse_args():
    p = argparse.ArgumentParser(description="Light pipe disc G-code generator")
    p.add_argument("--count", type=int, default=2,
                   help="Number of discs to cut (default: 2)")
    return p.parse_args()


def generate(count):
    lines = []

    def emit(line=""):
        lines.append(line)

    cut_r = (disc_d - tool_dia) / 2.0  # = 1mm

    total_depth = plexi_thickness + extra_depth

    emit(f"(Light pipe discs — {count}x ø{disc_d}mm × {plexi_thickness}mm plexiglass)")
    emit(f"(Tool: {tool_dia}mm single flute downcut)")
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

    for n in range(count):
        cx = n * disc_spacing
        cy = 0

        emit(f"(=== DISC {n+1} at X{cx:.1f} Y{cy:.1f} ===)")
        start_x = cx + cut_r
        emit(f"G0 Z{safe_z}")
        emit(f"G0 X{start_x:.3f} Y{cy:.3f}")

        z = 0
        n_passes = math.ceil(total_depth / depth_per_pass)
        for i in range(n_passes):
            z = max(z - depth_per_pass, -total_depth)
            emit(f"G1 Z{z:.3f} F{feed_z}")
            emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{feed_xy}")

        # Spring pass
        emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{feed_xy}")
        emit(f"G0 Z{safe_z}")
        emit()

    emit("M5")
    emit("G0 X0 Y0")
    emit("M2")

    return "\n".join(lines)


if __name__ == "__main__":
    args = parse_args()
    print(generate(args.count))
