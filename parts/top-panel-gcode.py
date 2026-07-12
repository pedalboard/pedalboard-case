#!/usr/bin/env python3
"""
Generate G-code for pedalboard case top panel (Hammond 1590DD).

All coordinates derived from pedalboard-display KiCad PCB.
Origin: front-left corner of the top flat surface (case mounted open-side-down).
X+ = right, Y+ = rear, Z=0 = top surface, Z- = into material.

Top flat surface: 181.8 × 113.8 mm (from STEP model).
Bottom plate thickness: 2.5 mm.
PCB (174 × 111 mm) centered in the surface.

Usage:
    python3 top-panel-gcode.py > top-panel.nc
    python3 top-panel-gcode.py --tool-dia 3 --feed-xy 200 > top-panel.nc
"""

import argparse
import math
import sys

# === PARAMETERS ===

def parse_args():
    p = argparse.ArgumentParser(description="Pedalboard case top panel G-code generator")

    # Tool
    p.add_argument("--tool-dia", type=float, default=4.0,
                   help="Endmill diameter in mm (default: 4.0)")

    # Feeds & speeds
    p.add_argument("--feed-xy", type=float, default=300,
                   help="Cutting feed rate XY in mm/min (default: 300)")
    p.add_argument("--feed-z", type=float, default=100,
                   help="Plunge feed rate Z in mm/min (default: 100)")
    p.add_argument("--spindle-rpm", type=int, default=10000,
                   help="Spindle speed in RPM (default: 10000)")

    # Depths
    p.add_argument("--stock-thickness", type=float, default=2.5,
                   help="Case wall thickness in mm (default: 2.5)")
    p.add_argument("--depth-per-pass", type=float, default=0.3,
                   help="Depth of cut per pass in mm (default: 0.3)")
    p.add_argument("--extra-depth", type=float, default=0.2,
                   help="Extra depth below stock for clean through-cut (default: 0.2)")

    # Heights
    p.add_argument("--safe-z", type=float, default=5.0,
                   help="Safe Z height for rapids (default: 5.0)")
    p.add_argument("--retract-z", type=float, default=1.0,
                   help="Retract Z between passes (default: 1.0)")

    # Geometry overrides
    p.add_argument("--button-dia", type=float, default=22.3,
                   help="Button/encoder hole diameter (default: 22.3)")
    p.add_argument("--display-w", type=float, default=34.5,
                   help="Display cutout width (default: 34.5)")
    p.add_argument("--display-h", type=float, default=36.7,
                   help="Display cutout height (default: 36.7)")
    p.add_argument("--lightpipe-dia", type=float, default=6.0,
                   help="Light pipe hole diameter (default: 6.0)")
    p.add_argument("--bezel-hole-dia", type=float, default=4.0,
                   help="Bezel mounting hole diameter (default: 4.0)")

    return p.parse_args()


# === GEOMETRY ===
# Origin: front-left corner of the case top flat surface.
# Case mounted open-side-down on CNC table.
# Top flat surface (exterior bottom of casting): 181.8 × 113.8 mm
# PCB (174 × 111 mm) is centered in this surface.
#
# X+ = right, Y+ = toward rear of case.
# Z=0 = top flat surface, Z- = cutting into the case.
#
# From Hammond 1590DD STEP model:
#   Exterior bottom face: 181.84 × 113.84 mm
#   Bottom plate thickness: 2.5 mm
#   Draft angle: ~2° (walls taper inward toward bottom)

CASE_TOP_W = 181.8  # mm (X direction, probeable)
CASE_TOP_H = 113.8  # mm (Y direction, probeable)
PCB_W = 174.0
PCB_H = 111.0

# PCB centered in case top surface
PCB_OFFSET_X = (CASE_TOP_W - PCB_W) / 2.0  # ≈ 3.9 mm
PCB_OFFSET_Y = (CASE_TOP_H - PCB_H) / 2.0  # ≈ 1.4 mm

def pcb_to_cnc(kicad_x, kicad_y):
    """Convert KiCad coords to CNC coords.

    Origin: front-left corner of case top flat surface.
    X+ = right, Y+ = toward rear.
    KiCad PCB origin: (20, 25) from PCB top-left.
    """
    pcb_x = kicad_x - 20.0  # KiCad → PCB top-left relative
    pcb_y = kicad_y - 25.0
    cnc_x = PCB_OFFSET_X + pcb_x
    cnc_y = PCB_OFFSET_Y + pcb_y
    return (cnc_x, cnc_y)

BUTTONS = [
    pcb_to_cnc(32, 72),    # B1
    pcb_to_cnc(32, 124),   # B2
    pcb_to_cnc(107, 72),   # B3
    pcb_to_cnc(107, 124),  # B4
    pcb_to_cnc(182, 72),   # B5
    pcb_to_cnc(182, 124),  # B6
]

ENCODERS = [
    pcb_to_cnc(70, 39),    # E1
    pcb_to_cnc(145, 39),   # E2
]

DISPLAYS = [
    pcb_to_cnc(69.5, 101.2),   # D1 (footprint center)
    pcb_to_cnc(144.5, 101.2),  # D2 (footprint center)
]

LIGHT_PIPES = [
    pcb_to_cnc(94.5, 53),     # LED1
    pcb_to_cnc(119.5, 53),    # LED2
]

# Bezel holes: ±15mm X, ±26mm Y from each display center
def bezel_holes():
    holes = []
    for dx, dy in DISPLAYS:
        for sx in [-1, 1]:
            for sy in [-1, 1]:
                holes.append((dx + sx * 15.0, dy + sy * 26.0))
    return holes

BEZEL_HOLES = bezel_holes()


# === G-CODE GENERATION ===

class GCode:
    def __init__(self, args):
        self.args = args
        self.tool_r = args.tool_dia / 2.0
        self.total_depth = args.stock_thickness + args.extra_depth
        self.lines = []

    def emit(self, line=""):
        self.lines.append(line)

    def header(self):
        a = self.args
        self.emit(f"(Pedalboard case top panel)")
        self.emit(f"(Origin: front-left corner of top flat surface)")
        self.emit(f"(Case mounted open-side-down, surface 181.8 x 113.8 mm)")
        self.emit(f"(Tool: {a.tool_dia}mm single flute downcut)")
        self.emit(f"(Feed XY: {a.feed_xy} mm/min, Z: {a.feed_z} mm/min)")
        self.emit(f"(Spindle: {a.spindle_rpm} RPM)")
        self.emit(f"(Stock: {a.stock_thickness}mm, depth/pass: {a.depth_per_pass}mm)")
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

    def circular_profile(self, cx, cy, diameter, label=""):
        """Cut a circular through-hole using helical interpolation."""
        a = self.args
        r = diameter / 2.0
        cut_r = r - self.tool_r  # toolpath radius

        if cut_r <= 0:
            # Hole smaller than or equal to tool: plunge
            self.plunge_hole(cx, cy, label)
            return

        self.emit()
        self.emit(f"({label}: circle ø{diameter}mm at X{cx:.1f} Y{cy:.1f})")

        # Rapid to start position (3 o'clock)
        start_x = cx + cut_r
        start_y = cy
        self.rapid_to(start_x, start_y)

        # Helical descent
        n_passes = math.ceil(self.total_depth / a.depth_per_pass)
        self.emit(f"G0 Z{a.retract_z}")

        current_z = 0
        for i in range(n_passes):
            current_z -= a.depth_per_pass
            if current_z < -self.total_depth:
                current_z = -self.total_depth
            # Full circle with Z descent (helical)
            self.emit(f"G1 Z{current_z:.3f} F{a.feed_z}")
            self.emit(f"G2 X{start_x:.3f} Y{start_y:.3f} I{-cut_r:.3f} J0 Z{current_z:.3f} F{a.feed_xy}")

        # Final full-depth pass (spring cut)
        self.emit(f"G2 X{start_x:.3f} Y{start_y:.3f} I{-cut_r:.3f} J0 F{a.feed_xy}")

        # Retract
        self.emit(f"G0 Z{a.safe_z}")

    def rectangular_profile(self, cx, cy, width, height, label=""):
        """Cut a rectangular through-hole with corner radius = tool radius."""
        a = self.args
        corner_r = self.tool_r  # minimum corner radius with this tool

        # Toolpath rectangle (offset inward by tool radius)
        hw = width / 2.0 - self.tool_r   # half-width of toolpath
        hh = height / 2.0 - self.tool_r  # half-height of toolpath

        self.emit()
        self.emit(f"({label}: rect {width}×{height}mm at X{cx:.1f} Y{cy:.1f}, corner R{corner_r:.1f})")

        # Start at mid-point of bottom edge
        start_x = cx
        start_y = cy - hh
        self.rapid_to(start_x, start_y)

        n_passes = math.ceil(self.total_depth / a.depth_per_pass)
        self.emit(f"G0 Z{a.retract_z}")

        current_z = 0
        for i in range(n_passes):
            current_z -= a.depth_per_pass
            if current_z < -self.total_depth:
                current_z = -self.total_depth

            self.emit(f"G1 Z{current_z:.3f} F{a.feed_z}")

            # Rectangle path: CCW from bottom-center
            # → bottom-right corner
            self.emit(f"G1 X{cx + hw:.3f} Y{cy - hh:.3f} F{a.feed_xy}")
            # ↑ right side
            self.emit(f"G1 X{cx + hw:.3f} Y{cy + hh:.3f}")
            # ← top-left corner
            self.emit(f"G1 X{cx - hw:.3f} Y{cy + hh:.3f}")
            # ↓ left side
            self.emit(f"G1 X{cx - hw:.3f} Y{cy - hh:.3f}")
            # → back to start
            self.emit(f"G1 X{cx:.3f} Y{cy - hh:.3f}")

        # Spring pass at full depth
        self.emit(f"G1 X{cx + hw:.3f} Y{cy - hh:.3f} F{a.feed_xy}")
        self.emit(f"G1 X{cx + hw:.3f} Y{cy + hh:.3f}")
        self.emit(f"G1 X{cx - hw:.3f} Y{cy + hh:.3f}")
        self.emit(f"G1 X{cx - hw:.3f} Y{cy - hh:.3f}")
        self.emit(f"G1 X{cx:.3f} Y{cy - hh:.3f}")

        self.emit(f"G0 Z{a.safe_z}")

    def plunge_hole(self, cx, cy, label=""):
        """Plunge-drill a hole equal to tool diameter."""
        a = self.args
        self.emit()
        self.emit(f"({label}: plunge ø{a.tool_dia}mm at X{cx:.1f} Y{cy:.1f})")
        self.rapid_to(cx, cy)
        self.emit(f"G0 Z{a.retract_z}")

        # Peck drill
        current_z = 0
        peck = a.depth_per_pass * 2  # pecks can be deeper for plunge
        while current_z > -self.total_depth:
            current_z -= peck
            if current_z < -self.total_depth:
                current_z = -self.total_depth
            self.emit(f"G1 Z{current_z:.3f} F{a.feed_z}")
            self.emit(f"G0 Z{a.retract_z}")

        # Final plunge
        self.emit(f"G1 Z{-self.total_depth:.3f} F{a.feed_z}")
        self.emit(f"G0 Z{a.safe_z}")

    def generate(self):
        a = self.args
        self.header()

        # 1. Bezel mounting holes (smallest, least stress on part)
        self.emit()
        self.emit("(=== BEZEL MOUNTING HOLES ===)")
        for i, (x, y) in enumerate(BEZEL_HOLES):
            self.circular_profile(x, y, a.bezel_hole_dia, f"Bezel hole {i+1}")

        # 2. Light pipe holes
        self.emit()
        self.emit("(=== LIGHT PIPE HOLES ===)")
        for i, (x, y) in enumerate(LIGHT_PIPES):
            self.circular_profile(x, y, a.lightpipe_dia, f"Light pipe {i+1}")

        # 3. Button/encoder holes
        self.emit()
        self.emit("(=== BUTTON HOLES ===)")
        for i, (x, y) in enumerate(BUTTONS):
            self.circular_profile(x, y, a.button_dia, f"Button {i+1}")

        self.emit()
        self.emit("(=== ENCODER HOLES ===)")
        for i, (x, y) in enumerate(ENCODERS):
            self.circular_profile(x, y, a.button_dia, f"Encoder {i+1}")

        # 4. Display cutouts (largest, do last)
        self.emit()
        self.emit("(=== DISPLAY CUTOUTS ===)")
        for i, (x, y) in enumerate(DISPLAYS):
            self.rectangular_profile(x, y, a.display_w, a.display_h, f"Display {i+1}")

        self.footer()
        return "\n".join(self.lines)


if __name__ == "__main__":
    args = parse_args()

    # Validate
    if args.tool_dia > args.lightpipe_dia:
        print(f"WARNING: Tool ø{args.tool_dia}mm > light pipe hole ø{args.lightpipe_dia}mm, "
              f"will plunge (hole = tool diameter)", file=sys.stderr)
    if args.tool_dia > args.bezel_hole_dia:
        print(f"WARNING: Tool ø{args.tool_dia}mm > bezel hole ø{args.bezel_hole_dia}mm, "
              f"will plunge (hole = tool diameter)", file=sys.stderr)

    gc = GCode(args)
    print(gc.generate())
