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
depth_per_pass = 0.25   # mm — clean finish in plexiglass
extra_depth = 0.5       # mm — cut well past material on final pass
plexi_thickness = 2.0   # mm
total_depth = plexi_thickness + extra_depth

def through_depths():
    """Z depths for through-cuts: passes at 0.5mm increments, skipping 2.0mm,
    final pass goes directly to -2.5mm for clean separation."""
    depths = []
    z = 0
    while z > -(plexi_thickness - depth_per_pass):
        z -= depth_per_pass
        depths.append(z)
    depths.append(-total_depth)
    return depths

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

# Spacing (must account for tool radius on external contours)
part_gap = 10.0         # mm between part edges (includes tool clearance)


def parse_args():
    p = argparse.ArgumentParser(description="Plexiglass parts G-code")
    p.add_argument("--rings", type=int, default=1,
                   help="Number of LED rings (default: 1)")
    p.add_argument("--windows", type=int, default=1,
                   help="Number of display windows (default: 1)")
    p.add_argument("--discs", type=int, default=1,
                   help="Number of light pipe discs (default: 1)")
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
    """Cut a circular internal contour to depth."""
    cut_r = (diameter - tool_dia) / 2.0
    if cut_r <= 0:
        # Peck drill
        rapid_to(cx, cy)
        for z in through_depths():
            emit(f"G1 Z{z:.3f} F{feed_z}")
            emit(f"G0 Z{safe_z}")
        return

    start_x = cx + cut_r
    rapid_to(start_x, cy)
    if depth >= plexi_thickness:
        depths = through_depths()
    else:
        depths = []
        z = 0
        while z > -depth:
            z = max(z - depth_per_pass, -depth)
            depths.append(z)
    for z in depths:
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
    # 1. Center hole (internal contour, full depth)
    circle_at(cx, cy, led_ring_center_d, total_depth)
    # 2. Step cut at ø22mm (external, 1mm deep — creates the ledge)
    cut_r = (led_ring_step_od + tool_dia) / 2.0
    start_x = cx + cut_r
    rapid_to(start_x, cy)
    z = 0
    n_passes = math.ceil(step_depth / depth_per_pass)
    for i in range(n_passes):
        z = max(z - depth_per_pass, -step_depth)
        emit(f"G1 Z{z:.3f} F{feed_z}")
        emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{feed_xy}")
    emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{feed_xy}")
    emit(f"G0 Z{safe_z}")
    # 3. Outer cut at ø24mm (external, full depth — separates the part)
    cut_r = (led_ring_od + tool_dia) / 2.0
    start_x = cx + cut_r
    rapid_to(start_x, cy)
    for z in through_depths():
        emit(f"G1 Z{z:.3f} F{feed_z}")
        emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{feed_xy}")
    emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{feed_xy}")
    emit(f"G0 Z{safe_z}")


def rect_external_at(cx, cy, width, height, depth):
    """Cut a rectangular external contour (tool outside the part)."""
    hw = width / 2.0 + tool_r
    hh = height / 2.0 + tool_r

    start_x = cx
    start_y = cy - hh
    rapid_to(start_x, start_y)

    if depth >= plexi_thickness:
        depths = through_depths()
    else:
        depths = []
        z = 0
        while z > -depth:
            z = max(z - depth_per_pass, -depth)
            depths.append(z)

    for z in depths:
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


def cut_display_window(cx, cy):
    """Cut one display window at (cx, cy)."""
    emit(f"")
    emit(f"(--- Display window at X{cx:.1f} Y{cy:.1f} ---)")
    # 1. Step cut at smaller size (external, 1mm deep — creates the ledge)
    rect_external_at(cx, cy, display_step_w, display_step_h, step_depth)
    # 2. Outer cut at larger size (external, full depth — separates the part)
    rect_external_at(cx, cy, display_top_w, display_top_h, total_depth)


def cut_lightpipe_disc(cx, cy):
    """Cut one light pipe disc at (cx, cy)."""
    emit(f"")
    emit(f"(--- Light pipe disc at X{cx:.1f} Y{cy:.1f} ---)")
    # External contour — tool follows outside the disc
    cut_r = (lightpipe_d + tool_dia) / 2.0  # tool center radius outside disc
    start_x = cx + cut_r
    rapid_to(start_x, cy)
    for z in through_depths():
        emit(f"G1 Z{z:.3f} F{feed_z}")
        emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{feed_xy}")
    # Spring pass
    emit(f"G2 X{start_x:.3f} Y{cy:.3f} I{-cut_r:.3f} J0 F{feed_xy}")
    emit(f"G0 Z{safe_z}")


# === MAIN ===

if __name__ == "__main__":
    args = parse_args()

    if args.production:
        n_rings = 8
        n_windows = 2
        n_discs = 2
    else:
        n_rings = args.rings
        n_windows = args.windows
        n_discs = args.discs

    job_name = f"{n_rings}x ring, {n_windows}x window, {n_discs}x disc"

    emit(f"({job_name})")
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

    # Layout parts optimally — fit within ~200mm x ~150mm sheet
    # Row 1: LED rings (up to 4 per row)
    rings_per_row = 4
    ring_pitch = led_ring_od + part_gap  # 34mm

    for i in range(n_rings):
        row = i // rings_per_row
        col = i % rings_per_row
        cx = col * ring_pitch + led_ring_od / 2.0
        cy = -(row * (led_ring_od + part_gap))
        cut_led_ring(cx, cy)

    # Calculate Y start for next section
    ring_rows = math.ceil(n_rings / rings_per_row)
    y_after_rings = -(ring_rows * (led_ring_od + part_gap))

    # Display windows row
    window_pitch = display_top_w + part_gap  # 46.5mm
    y_windows = y_after_rings - display_top_h / 2.0

    for i in range(n_windows):
        cx = i * window_pitch + display_top_w / 2.0
        cy = y_windows
        cut_display_window(cx, cy)

    # Light pipe discs — fit next to or below windows
    y_discs = y_windows - display_top_h / 2.0 - part_gap - lightpipe_d / 2.0
    disc_pitch = lightpipe_d + part_gap  # 16mm

    for i in range(n_discs):
        cx = i * disc_pitch + lightpipe_d / 2.0
        cy = y_discs
        cut_lightpipe_disc(cx, cy)

    emit()
    emit("M5")
    emit("G0 X0 Y0")
    emit("M2")

    print("\n".join(lines))
