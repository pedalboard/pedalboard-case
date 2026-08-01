#!/usr/bin/env python3
"""
Generate 1:1 printable SVG template for Hammond 1590DD side panel holes.

Print at 100% scale on A4. Cut out each strip, wrap around the case side,
and use as a drill guide.
"""

import sys

# Case dimensions (outer)
case_length = 188.0  # mm (long axis)
case_width = 120.0   # mm (short axis)
case_height = 37.0   # mm

# Heights from case bottom
pcb_top = 16.4
jack_height = pcb_top + 8      # 24.4mm
usb_height = pcb_top + 4       # 20.4mm
barrel_height = 25.5

# Hole positions: (distance_along_wall, height_from_bottom, diameter, label)
left_side = [
    (32.0, jack_height, 10, "J8"),
    (73.0, jack_height, 10, "J20"),
    (93.2, jack_height, 10, "J19"),
]

right_side = [
    (15.8, jack_height, 10, "J5"),
    (56.8, jack_height, 10, "J18"),
    (77.0, jack_height, 10, "J22"),
]

back_side = [
    (37.6, usb_height, 8, "J10 USB"),
    (74.5, jack_height, 6, "J1 MIDI"),
    (104.5, jack_height, 6, "J3 MIDI"),
    (161.0, barrel_height, 8, "J7 PWR"),
]


def svg_strip(holes, strip_length, strip_height, title):
    """Generate SVG for one side strip."""
    margin = 10
    w = strip_length + 2 * margin
    h = strip_height + 2 * margin + 15  # extra for title

    lines = []
    lines.append(f'<g>')
    lines.append(f'  <text x="{margin}" y="12" font-size="4" font-family="sans-serif">{title} ({strip_length:.0f}mm x {strip_height:.0f}mm)</text>')

    # Outline
    lines.append(f'  <rect x="{margin}" y="{margin + 15}" width="{strip_length}" height="{strip_height}" '
                 f'fill="none" stroke="black" stroke-width="0.3"/>')

    # Holes
    for dist, height, dia, label in holes:
        cx = margin + dist
        cy = margin + 15 + (strip_height - height)  # flip Y (bottom = high Y in SVG)
        r = dia / 2.0
        lines.append(f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="red" stroke-width="0.3"/>')
        # Crosshair
        lines.append(f'  <line x1="{cx-r-1}" y1="{cy}" x2="{cx+r+1}" y2="{cy}" stroke="red" stroke-width="0.15"/>')
        lines.append(f'  <line x1="{cx}" y1="{cy-r-1}" x2="{cx}" y2="{cy+r+1}" stroke="red" stroke-width="0.15"/>')
        # Label
        lines.append(f'  <text x="{cx}" y="{cy - r - 2}" font-size="3" font-family="sans-serif" '
                     f'text-anchor="middle" fill="red">{label} dia {dia}</text>')

    # Height markers
    lines.append(f'  <text x="{margin - 1}" y="{margin + 15 + strip_height + 4}" '
                 f'font-size="2.5" font-family="sans-serif">bottom edge</text>')
    lines.append(f'  <text x="{margin - 1}" y="{margin + 15 - 2}" '
                 f'font-size="2.5" font-family="sans-serif">top edge</text>')

    lines.append(f'</g>')
    return lines, w, h


# Generate full SVG with all three strips
svg_parts = []
total_height = 0
max_width = 0

strips = [
    ("Left side (looking from front)", left_side, case_length, case_height),
    ("Right side (looking from front)", right_side, case_length, case_height),
    ("Back (long edge)", back_side, case_length, case_height),
]

y_offset = 0
for title, holes, length, height in strips:
    part_lines, w, h = svg_strip(holes, length, height, title)
    svg_parts.append((y_offset, part_lines))
    y_offset += h + 5
    max_width = max(max_width, w)

total_height = y_offset

# A4 landscape: 297x210mm
page_w = 297
page_h = 210

svg = []
svg.append(f'<?xml version="1.0" encoding="UTF-8"?>')
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'width="{page_w}mm" height="{page_h}mm" '
           f'viewBox="0 0 {page_w} {page_h}">')

# Center on page
x_off = (page_w - max_width) / 2
y_off = (page_h - total_height) / 2

for y, lines in svg_parts:
    svg.append(f'<g transform="translate({x_off},{y_off + y})">')
    svg.extend(lines)
    svg.append('</g>')

svg.append('</svg>')

print('\n'.join(svg))
