#!/usr/bin/env python3
"""
Generate G-code for milling the CNC fixture plate for the Hammond 1590DD.

The fixture plate is cut from 15mm MDF and screws to the SRcnc wasteboard
via M5 carriage holes. The case then screws to the plate via #6-32 corner holes.

Origin: center of plate = machine X110 Y190 (wasteboard carriage hole center).

Features:
  - 4x case screw holes (ø3.6mm through + ø7mm counterbore, depth 4mm)
  - 4x carriage holes (ø5mm through + ø9.5mm countersink from bottom)

Usage:
    python3 fixture-plate-gcode.py > ../generated/fixture-plate.nc
    python3 fixture-plate-gcode.py --tool-dia 4 --feed-xy 800 > ../generated/fixture-plate.nc
"""

import argparse
import math
import sys

# === FIXTURE GEOMETRY ===

# Case screw holes — counterbored for ø10mm washer + shank through hole
CASE_HOLE_X = 89.0
CASE_HOLE_Y = 57.0
CASE_CLEARANCE_D = 4.0   # mm — shank clearance (peck drill with 4mm tool)
CASE_CBORE_D = 11.0       # mm — counterbore for ø10mm washer (+ 0.5mm clearance)
CASE_CBORE_DEPTH = 11.0   # mm — leaves 4mm MDF below washer
                          # min screw length ~10mm (4mm plate + ~4-6mm into case boss)

# Carriage holes — M5 through hole, screw head sits on top
CARRIAGE_HOLE_X = 60.0
CARRIAGE_HOLE_Y = 90.0
CARRIAGE_CLEARANCE_D = 5.4  # mm — M5 clearance


def parse_args():
    p = argparse.ArgumentParser(description="Fixture plate G-code generator")
    p.add_argument("--tool-dia", type=float, default=4.0,
                   help="Endmill diameter in mm (default: 4.0)")
    p.add_argument("--feed-xy", type=float, default=800,
                   help="Cutting feed rate XY in mm/min (default: 800)")
    p.add_argument("--feed-z", type=float, default=150,
                   help="Plunge feed rate Z in mm/min (default: 150)")
    p.add_argument("--spindle-rpm", type=int, default=10000,
                   help="Spindle speed in RPM (default: 10000)")
    p.add_argument("--stock-thickness", type=float, default=15.0,
                   help="MDF thickness in mm (default: 15.0)")
    p.add_argument("--depth-per-pass", type=float, default=0.5,
                   help="Depth of cut per pass in mm (default: 0.5)")
    p.add_argument("--extra-depth", type=float, default=0.5,
                   help="Extra depth below stock for clean through-cut (default: 0.5)")
    p.add_argument("--safe-z", type=float, default=5.0,
                   help="Safe Z height for rapids (default: 5.0)")
    return p.parse_args()


class GCode:
    def __init__(self, args):
        self.args = args
        self.tool_r = args.tool_dia / 2.0
        self.lines = []

    def emit(self, line=""):
        self.lines.append(line)

    def header(self):
        a = self.args
        self.emit("(Fixture plate for Hammond 1590DD top panel milling)")
        self.emit("(Origin: plate center = wasteboard carriage hole center)")
        self.emit("(Material: 15mm MDF — cut on the SRcnc)")
        self.emit(f"(Tool: {a.tool_dia}mm single flute endmill)")
        self.emit(f"(Feed XY: {a.feed_xy} mm/min, Z: {a.feed_z} mm/min)")
        self.emit(f"(Spindle: {a.spindle_rpm} RPM)")
        self.emit()
        self.emit("G21 (mm)")
        self.emit("G90 (absolute)")
        self.emit("G17 (XY plane)")
        self.emit()
        self.emit(f"M3 S{a.spindle_rpm}")
        self.emit("G4 P2 (spindle spin-up)")
        self.emit()

    def footer(self):
        self.emit()
        self.emit(f"G0 Z{self.args.safe_z}")
        self.emit("M5")
        self.emit("G0 X0 Y0")
        self.emit("M2")

    def rapid_to(self, x, y):
        self.emit(f"G0 Z{self.args.safe_z}")
        self.emit(f"G0 X{x:.3f} Y{y:.3f}")

    def helical_bore(self, cx, cy, diameter, depth, label=""):
        """Cut a circular hole using helical interpolation."""
        a = self.args
        cut_r = diameter / 2.0 - self.tool_r

        self.emit()
        self.emit(f"({label}: ø{diameter}mm at X{cx:.1f} Y{cy:.1f}, depth {depth}mm)")

        if cut_r <= 0:
            # Hole ≤ tool diameter — peck drill
            self.rapid_to(cx, cy)
            self.emit(f"G0 Z{a.safe_z}")
            current_z = 0
            while current_z > -depth:
                current_z = max(current_z - a.depth_per_pass * 2, -depth)
                self.emit(f"G1 Z{current_z:.3f} F{a.feed_z}")
                self.emit(f"G0 Z{a.safe_z}")
            self.emit(f"G0 Z{a.safe_z}")
            return

        start_x = cx + cut_r
        self.rapid_to(start_x, cy)
        self.emit(f"G0 Z1.0")

        n_passes = math.ceil(depth / a.depth_per_pass)
        current_z = 0
        for _ in range(n_passes):
            current_z = max(current_z - a.depth_per_pass, -depth)
            self.emit(f"G1 Z{current_z:.3f} F{a.feed_z}")
            self.emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 Z{current_z:.3f} F{a.feed_xy}")

        # Spring pass at full depth
        self.emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{a.feed_xy}")
        self.emit(f"G0 Z{a.safe_z}")

    def through_hole(self, cx, cy, diameter, label=""):
        """Cut a through hole (full stock thickness + extra depth)."""
        total = self.args.stock_thickness + self.args.extra_depth
        self.helical_bore(cx, cy, diameter, total, label)

    def generate(self):
        self.header()

        # Case screw holes — 4 corners + 2 center long sides
        self.emit("(=== CASE SCREW HOLES (ø11mm counterbore 11mm deep + ø4mm through) ===)")
        case_positions = [
            (-CASE_HOLE_X, -CASE_HOLE_Y),
            ( CASE_HOLE_X, -CASE_HOLE_Y),
            ( CASE_HOLE_X,  CASE_HOLE_Y),
            (-CASE_HOLE_X,  CASE_HOLE_Y),
            (0,            -CASE_HOLE_Y),  # center long side
            (0,             CASE_HOLE_Y),  # center long side
        ]
        for i, (x, y) in enumerate(case_positions):
            self.helical_bore(x, y, CASE_CBORE_D, CASE_CBORE_DEPTH,
                              f"Case hole {i+1} counterbore")
            self.through_hole(x, y, CASE_CLEARANCE_D,
                              f"Case hole {i+1} shank")

        # Carriage holes — M5 through hole (screw head sits on top)
        self.emit()
        self.emit("(=== CARRIAGE HOLES (M5 through hole) ===)")
        for i, (x, y) in enumerate([
            (-CARRIAGE_HOLE_X, -CARRIAGE_HOLE_Y),
            ( CARRIAGE_HOLE_X, -CARRIAGE_HOLE_Y),
            ( CARRIAGE_HOLE_X,  CARRIAGE_HOLE_Y),
            (-CARRIAGE_HOLE_X,  CARRIAGE_HOLE_Y),
        ]):
            self.through_hole(x, y, CARRIAGE_CLEARANCE_D,
                              f"Carriage hole {i+1}")

        self.footer()
        return "\n".join(self.lines)


if __name__ == "__main__":
    args = parse_args()
    gc = GCode(args)
    print(gc.generate())
