#!/usr/bin/env python3
"""
Generate a 1:1 SVG layout template for plexiglass part placement.
Print at 100% scale, lay on the sheet to mark tape positions.

Usage:
    python3 plexi-cut-layout.py > plexi-cut-layout.svg
    python3 plexi-cut-layout.py --production > plexi-production-layout.svg
"""

import argparse
import math

# Part dimensions (same as plexi-cut.py)
led_ring_od = 24.0
led_ring_step_od = 22.0
led_ring_center_d = 14.0
display_top_w = 36.5
display_top_h = 38.7
display_step_w = 34.1
display_step_h = 36.3
lightpipe_d = 6.0
part_gap = 10.0
rings_per_row = 4


def parse_args():
    p = argparse.ArgumentParser(description="Plexiglass layout SVG")
    p.add_argument("--rings", type=int, default=1)
    p.add_argument("--windows", type=int, default=1)
    p.add_argument("--discs", type=int, default=1)
    p.add_argument("--production", action="store_true")
    return p.parse_args()


def generate_svg(n_rings, n_windows, n_discs):
    parts = []  # (type, cx, cy)

    # LED rings layout
    ring_pitch = led_ring_od + part_gap
    for i in range(n_rings):
        row = i // rings_per_row
        col = i % rings_per_row
        cx = col * ring_pitch + led_ring_od / 2.0
        cy = row * (led_ring_od + part_gap)
        parts.append(("ring", cx, cy))

    # Display windows
    ring_rows = math.ceil(n_rings / rings_per_row) if n_rings > 0 else 0
    y_after_rings = ring_rows * (led_ring_od + part_gap)
    window_pitch = display_top_w + part_gap
    y_windows = y_after_rings + display_top_h / 2.0

    for i in range(n_windows):
        cx = i * window_pitch + display_top_w / 2.0
        cy = y_windows
        parts.append(("window", cx, cy))

    # Light pipe discs
    y_discs = y_windows + display_top_h / 2.0 + part_gap + lightpipe_d / 2.0
    disc_pitch = lightpipe_d + part_gap

    for i in range(n_discs):
        cx = i * disc_pitch + lightpipe_d / 2.0
        cy = y_discs
        parts.append(("disc", cx, cy))

    # Calculate bounds
    margin = 15.0
    max_x = max(cx for _, cx, _ in parts) + led_ring_od / 2.0 + margin
    max_y = max(cy for _, _, cy in parts) + display_top_h / 2.0 + margin

    # SVG output (1mm = 1 SVG unit, viewBox in mm)
    width_mm = max_x + margin
    height_mm = max_y + margin

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'width="{width_mm}mm" height="{height_mm}mm" '
               f'viewBox="0 0 {width_mm} {height_mm}">')
    svg.append(f'<title>Plexiglass part layout — {n_rings} rings, {n_windows} windows, {n_discs} discs</title>')

    # Background
    svg.append(f'<rect x="0" y="0" width="{width_mm}" height="{height_mm}" fill="white"/>')

    # Mirror the content (viewing from bottom/tape side)
    svg.append(f'<g transform="translate({width_mm},0) scale(-1,1)">')

    # Origin crosshair
    ox, oy = margin, margin
    svg.append(f'<line x1="{ox-5}" y1="{oy}" x2="{ox+5}" y2="{oy}" stroke="red" stroke-width="0.3"/>')
    svg.append(f'<line x1="{ox}" y1="{oy-5}" x2="{ox}" y2="{oy+5}" stroke="red" stroke-width="0.3"/>')
    svg.append(f'<text x="{ox+2}" y="{oy-2}" font-size="3" fill="red">X0 Y0</text>')

    for ptype, cx, cy in parts:
        # Offset by margin
        x = cx + margin
        y = cy + margin

        if ptype == "ring":
            # Outer contour (cut line)
            svg.append(f'<circle cx="{x}" cy="{y}" r="{led_ring_od/2}" '
                       f'fill="none" stroke="blue" stroke-width="0.3"/>')
            # Step contour
            svg.append(f'<circle cx="{x}" cy="{y}" r="{led_ring_step_od/2}" '
                       f'fill="none" stroke="blue" stroke-width="0.2" stroke-dasharray="1,1"/>')
            # Center hole
            svg.append(f'<circle cx="{x}" cy="{y}" r="{led_ring_center_d/2}" '
                       f'fill="none" stroke="blue" stroke-width="0.3"/>')
            # Tape position (crosshair)
            svg.append(f'<circle cx="{x}" cy="{y}" r="1" fill="green" opacity="0.5"/>')
            svg.append(f'<text x="{x-4}" y="{y+led_ring_od/2+3}" font-size="2.5" fill="black">Ring</text>')

        elif ptype == "window":
            # Outer contour
            svg.append(f'<rect x="{x-display_top_w/2}" y="{y-display_top_h/2}" '
                       f'width="{display_top_w}" height="{display_top_h}" rx="2" '
                       f'fill="none" stroke="blue" stroke-width="0.3"/>')
            # Step contour
            svg.append(f'<rect x="{x-display_step_w/2}" y="{y-display_step_h/2}" '
                       f'width="{display_step_w}" height="{display_step_h}" rx="2" '
                       f'fill="none" stroke="blue" stroke-width="0.2" stroke-dasharray="1,1"/>')
            # Tape position
            svg.append(f'<circle cx="{x}" cy="{y}" r="1" fill="green" opacity="0.5"/>')
            svg.append(f'<text x="{x-6}" y="{y+display_top_h/2+3}" font-size="2.5" fill="black">Display</text>')

        elif ptype == "disc":
            # Outer contour
            svg.append(f'<circle cx="{x}" cy="{y}" r="{lightpipe_d/2}" '
                       f'fill="none" stroke="blue" stroke-width="0.3"/>')
            # Tape position
            svg.append(f'<circle cx="{x}" cy="{y}" r="0.5" fill="green" opacity="0.5"/>')
            svg.append(f'<text x="{x-3}" y="{y+lightpipe_d/2+3}" font-size="2" fill="black">Disc</text>')

    # Close mirror group
    svg.append('</g>')

    # Legend (not mirrored)
    ly = height_mm - 8
    svg.append(f'<text x="5" y="{ly}" font-size="3" fill="black">'
               f'BOTTOM VIEW (tape side) — mirrored from cutting side</text>')
    svg.append(f'<text x="5" y="{ly+4}" font-size="3" fill="black">'
               f'Blue = cut lines | Green dots = tape positions | Print at 100% scale (1:1)</text>')

    svg.append('</svg>')
    return '\n'.join(svg)


if __name__ == "__main__":
    args = parse_args()
    if args.production:
        n_rings, n_windows, n_discs = 8, 2, 2
    else:
        n_rings, n_windows, n_discs = args.rings, args.windows, args.discs

    print(generate_svg(n_rings, n_windows, n_discs))
