#!/usr/bin/env python3
"""
Generate G-code for test-cutting all plexiglass parts in one job.

Cuts one of each part from a single 2mm plexiglass sheet:
- 1x LED ring (ø24mm, stepped, ø14mm center hole)
- 1x Display window (36.5×38.7mm, stepped)
- 1x Light pipe disc (ø6mm solid)

Parts are laid out in a row with spacing between them.
Origin: left edge of layout, Z0 = top of plexiglass.
Tool: 4mm single flute downcut endmill.

Usage:
    python3 plexi-test-cut.py > plexi-test-cut.nc
    python3 plexi-test-cut.py --production   # 8 rings, 2 windows, 2 discs
"""

import argparse
import math

# === PARAMETERS ===

tool_dia = 4.0
tool_r = tool_dia / 2.0

feed_xy = 500           # mm/min
feed_z = 100            # mm/min
spindle_rpm = 15000
safe_z = 15.0           # mm
depth_per_pass = 0.5    # mm
extra_depth = 0.3       # mm
plexi_thickness = 2.0   # mm
total_depth = plexi_thickness + extra_depth

# Part dimensions
led_ring_od = 24.0
led_ring_step_od = 22.0
led_ring_center_d = 14.0
step_depth = 1.0

display_top_w = 36.5
display_top_h = 38.7
display_step_w = 34.1
display_step_h = 36.3

lightpipe_d = 6.0

# Spacing
part_gap = 5.0          # mm between parts


def parse_args():
    p = argparse.ArgumentParser(description="Plexiglass parts G-code")
    p.add_argument("--production", action="store_true",
                   help="Production quantities: 8 rings, 2 windows, 2 discs")
    return p.parse_args()


# === G-CODE HELPERS ===

lines = []

def emit(line=""):
    lines.append(line)

def rapid_to(x, y):
    emit(f"G0 Z{safe_z}")
    emit(f"G0 X{x:.3f} Y{y:.3f}")

def circle_at(cx, cy, diameter, depth):
    """Cut a circular contour to depth."""
    cut_r = (diameter - tool_dia) / 2.0
    if cut_r <= 0:
        # Peck drill
        rapid_to(cx, cy)
        z = 0
        while z > -depth:
            z = max(z - depth_per_pass * 2, -depth)
            emit(f"G1 Z{z:.3f} F{feed_z}")
            emit(f"G0 Z{safe_z}")
        return

    start_x = cx + cut_r
    rapid_to(start_x, cy)
    z = 0
    n_passes = math.ceil(depth / depth_per_pass)
    for i in range(n_passes):
        z = max(z - depth_per_pass, -depth)
        emit(f"G1 Z{z:.3f} F{feed_z}")
        emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{feed_xy}")
    # Spring pass
    emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{feed_xy}")
    emit(f"G0 Z{safe_z}")

def rect_at(cx, cy, width, height, depth):
    """Cut a rectangular contour to depth."""
    hw = width / 2.0 - tool_r
    hh = height / 2.0 - tool_r

    start_x = cx
    start_y = cy - hh
    rapid_to(start_x, start_y)

    z = 0
    n_passes = math.ceil(depth / depth_per_pass)
    for i in range(n_passes):
        z = max(z - depth_per_pass, -depth)
        emit(f"G1 Z{z:.3f} F{feed_z}")
        emit(f"G1 X{cx + hw:.3f} Y{cy - hh:.3f} F{feed_xy}")
        emit(f"G1 X{cx + hw:.3f} Y{cy + hh:.3f}")
        emit(f"G1 X{cx - hw:.3f} Y{cy + hh:.3f}")
        emit(f"G1 X{cx - hw:.3f} Y{cy - hh:.3f}")
        emit(f"G1 X{cx:.3f} Y{cy - hh:.3f}")

    # Spring pass
    emit(f"G1 X{cx + hw:.3f} Y{cy - hh:.3f} F{feed_xy}")
    emit(f"G1 X{cx + hw:.3f} Y{cy + hh:.3f}")
    emit(f"G1 X{cx - hw:.3f} Y{cy + hh:.3f}")
    emit(f"G1 X{cx - hw:.3f} Y{cy - hh:.3f}")
    emit(f"G1 X{cx:.3f} Y{cy - hh:.3f}")
    emit(f"G0 Z{safe_z}")


def cut_led_ring(cx, cy):
    """Cut one LED ring at (cx, cy)."""
    emit(f"")
    emit(f"(--- LED ring at X{cx:.1f} Y{cy:.1f} ---)")
    # 1. Center hole
    circle_at(cx, cy, led_ring_center_d, total_depth)
    # 2. Outer lip (1mm deep)
    circle_at(cx, cy, led_ring_od, step_depth)
    # 3. Through cut at step diameter
    circle_at(cx, cy, led_ring_step_od, total_depth)


def cut_display_window(cx, cy):
    """Cut one display window at (cx, cy)."""
    emit(f"")
    emit(f"(--- Display window at X{cx:.1f} Y{cy:.1f} ---)")
    # 1. Outer lip (1mm deep)
    rect_at(cx, cy, display_top_w, display_top_h, step_depth)
    # 2. Through cut at step size
    rect_at(cx, cy, display_step_w, display_step_h, total_depth)


def cut_lightpipe_disc(cx, cy):
    """Cut one light pipe disc at (cx, cy)."""
    emit(f"")
    emit(f"(--- Light pipe disc at X{cx:.1f} Y{cy:.1f} ---)")
    circle_at(cx, cy, lightpipe_d, total_depth)


# === MAIN ===

if __name__ == "__main__":
    args = parse_args()

    if args.production:
        n_rings = 8
        n_windows = 2
        n_discs = 2
        job_name = "Production"
    else:
        n_rings = 1
        n_windows = 1
        n_discs = 1
        job_name = "Test cut"

    emit(f"({job_name}: {n_rings}x LED ring, {n_windows}x display window, {n_discs}x light pipe disc)")
    emit(f"(Tool: {tool_dia}mm single flute downcut)")
    emit(f"(Material: {plexi_thickness}mm plexiglass)")
    emit(f"(Feed: {feed_xy}mm/min XY, {feed_z}mm/min Z, {depth_per_pass}mm/pass)")
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

    # Layout parts in rows
    x_cursor = 0
    y_cursor = 0

    # LED rings
    for i in range(n_rings):
        cx = x_cursor + led_ring_od / 2.0
        cy = y_cursor
        cut_led_ring(cx, cy)
        x_cursor += led_ring_od + part_gap

    # Next row for display windows
    x_cursor = 0
    y_cursor -= (led_ring_od / 2.0 + display_top_h / 2.0 + part_gap)

    for i in range(n_windows):
        cx = x_cursor + display_top_w / 2.0
        cy = y_cursor
        cut_display_window(cx, cy)
        x_cursor += display_top_w + part_gap

    # Next row for light pipe discs
    x_cursor = 0
    y_cursor -= (display_top_h / 2.0 + lightpipe_d / 2.0 + part_gap)

    for i in range(n_discs):
        cx = x_cursor + lightpipe_d / 2.0
        cy = y_cursor
        cut_lightpipe_disc(cx, cy)
        x_cursor += lightpipe_d + part_gap

    emit()
    emit("M5")
    emit("G0 X0 Y0")
    emit("M2")

    print("\n".join(lines))
