#!/usr/bin/env python3
"""
Generate 1:1 printable SVG template for Hammond 1590DD side panel holes.

Print at 100% scale on A4. Cut out each strip, wrap around the case side,
and use as a drill guide.

Positions extracted from pedalboard-hw KiCad PCB.
"""

# Case dimensions (outer)
case_length = 188.0  # mm (long axis, back/front sides)
case_width = 120.0   # mm (short axis, left/right sides)
case_height = 37.0   # mm

# PCB dimensions
pcb_length = 174.0   # along case long axis
pcb_width = 111.0    # along case short axis

# PCB offset from case inner wall
# PCB sits against the back wall (no gap at back)
offset_long = (case_length - pcb_length) / 2.0   # 7mm (centered on long axis)
offset_short_back = 0.0                           # PCB touches back wall
offset_short_front = case_width - pcb_width       # 9mm gap at front

# KiCad PCB origin
kicad_origin_x = 20.0
kicad_origin_y = 25.0

# Heights from case TOP (template aligns to top edge)
# Split between jig values and new calculation (1mm compromise)
case_height_inner = 37.0  # mm (with bottom plate)
pcb_top_from_bottom = 15.4  # mm (compromise: jig=16.4, calc=14.4)

jack_from_top = case_height_inner - (pcb_top_from_bottom + 8)      # 13.6mm
jack_35_from_top = case_height_inner - (pcb_top_from_bottom + 2.5) # 19.1mm
usb_from_top = case_height_inner - (pcb_top_from_bottom + 4)       # 17.6mm

jack_height = jack_from_top
jack_35_height = jack_35_from_top
usb_height = usb_from_top
barrel_height = jack_from_top  # same as 6.35mm jacks

# USB-A connector dimensions
usb_width = 14.4   # mm
usb_height_dim = 8.0  # mm (vertical)

# KiCad connector positions
# Left/right sides: KiCad Y maps to position along the SHORT side (120mm)
# Back: KiCad X maps to position along the LONG side (188mm)

# Left side connectors (KiCad X ≈ 34.4, angle 180 = pointing left)
# Position along short side = offset_short_back + (kicad_y - kicad_origin_y)
left_side_kicad_y = [50.0, 91.0, 111.2]  # J8, J20, J19
left_side = []
for ky in left_side_kicad_y:
    pos = offset_short_back + (ky - kicad_origin_y)
    left_side.append(pos)

# Right side connectors (KiCad X ≈ 175.6, angle 0 = pointing right)
right_side_kicad_y = [33.8, 74.8, 95.0]  # J5, J18, J22
right_side = []
for ky in right_side_kicad_y:
    pos = offset_short_back + (ky - kicad_origin_y)
    right_side.append(pos)

# Back connectors (KiCad Y ≈ 24-31, various X)
# Position along long side = offset_long + (kicad_x - kicad_origin_x)
# Mirror: looking at the back from outside, left/right is flipped from PCB view
back_connectors_kicad_x = {
    'J10 USB': 53.1,
    'J1 MIDI': 90.0,
    'J3 MIDI': 120.0,
}

# Barrel jack is independent of PCB, fixed position from jig
BARREL_POS_OUTSIDE = 39.0  # mm from left, looking from outside back

# Hole data: (distance_from_left_edge, height, diameter, label)
# Left side (strip = 120mm wide, looking from outside)
# "from front" = from the front edge of the case
left_holes = [
    (left_side[0], jack_height, 10, "J8"),
    (left_side[1], jack_height, 10, "J20"),
    (left_side[2], jack_height, 10, "J19"),
]

# Right side (mirrored — looking from outside, back is on the right end)
right_holes = [
    (case_width - right_side[0], jack_height, 10, "J5"),
    (case_width - right_side[1], jack_height, 10, "J18"),
    (case_width - right_side[2], jack_height, 10, "J22"),
]

# Back (looking from outside the back, left/right is mirrored from PCB)
back_holes = []
for label, kx in back_connectors_kicad_x.items():
    pos_from_left_inside = offset_long + (kx - kicad_origin_x)
    # Mirror: looking from outside back, left = case_length - pos
    pos_from_left_outside = case_length - pos_from_left_inside
    if 'USB' in label:
        back_holes.append((pos_from_left_outside, usb_height, 0, label))
    else:
        back_holes.append((pos_from_left_outside, jack_35_height, 6, label))

# Barrel jack at fixed position (independent of PCB, same height as 6.35mm jacks)
back_holes.append((BARREL_POS_OUTSIDE, jack_height, 8, "J7 PWR"))


def svg_strip(holes, strip_length, strip_height, title, usb_slot=None):
    """Generate SVG for one side strip."""
    margin = 10
    w = strip_length + 2 * margin
    h = strip_height + 2 * margin + 15  # extra for title

    lines = []
    lines.append(f'<g>')
    lines.append(f'  <text x="{margin}" y="12" font-size="4" font-family="sans-serif">'
                 f'{title} ({strip_length:.0f}mm x {strip_height:.0f}mm)</text>')

    # Outline
    lines.append(f'  <rect x="{margin}" y="{margin + 15}" width="{strip_length}" height="{strip_height}" '
                 f'fill="none" stroke="black" stroke-width="0.3"/>')

    # Center line (horizontal, at middle height)
    center_y = margin + 15 + strip_height / 2.0
    lines.append(f'  <line x1="{margin}" y1="{center_y}" x2="{margin + strip_length}" y2="{center_y}" '
                 f'stroke="gray" stroke-width="0.15" stroke-dasharray="2,2"/>')
    lines.append(f'  <text x="{margin + strip_length + 1}" y="{center_y + 1}" '
                 f'font-size="2" font-family="sans-serif" fill="gray">{strip_height/2:.1f}mm</text>')

    # Center line (vertical, at middle of strip length)
    center_x = margin + strip_length / 2.0
    lines.append(f'  <line x1="{center_x}" y1="{margin + 15}" x2="{center_x}" y2="{margin + 15 + strip_height}" '
                 f'stroke="gray" stroke-width="0.15" stroke-dasharray="2,2"/>')
    lines.append(f'  <text x="{center_x + 1}" y="{margin + 15 - 2}" '
                 f'font-size="2" font-family="sans-serif" fill="gray">{strip_length/2:.0f}mm</text>')

    # Holes
    for dist, height, dia, label in holes:
        cx = margin + dist
        cy = margin + 15 + height  # height measured from top

        if dia == 0 and usb_slot:
            # USB-A rectangular slot — draw rectangle + two 8mm drill holes
            sw, sh = usb_slot
            lines.append(f'  <rect x="{cx - sw/2}" y="{cy - sh/2}" width="{sw}" height="{sh}" '
                         f'fill="none" stroke="red" stroke-width="0.3" stroke-dasharray="1,1"/>')
            # Center mark
            lines.append(f'  <line x1="{cx-2}" y1="{cy}" x2="{cx+2}" y2="{cy}" stroke="red" stroke-width="0.15"/>')
            lines.append(f'  <line x1="{cx}" y1="{cy-2}" x2="{cx}" y2="{cy+2}" stroke="red" stroke-width="0.15"/>')
            # Two 8mm holes at ends of slot (centers 6.4mm apart)
            drill_r = 4.0
            pilot_offset = sw / 2 - drill_r
            lines.append(f'  <circle cx="{cx - pilot_offset}" cy="{cy}" r="{drill_r}" '
                         f'fill="none" stroke="blue" stroke-width="0.3"/>')
            lines.append(f'  <circle cx="{cx + pilot_offset}" cy="{cy}" r="{drill_r}" '
                         f'fill="none" stroke="blue" stroke-width="0.3"/>')
            # Crosshairs on drill centers
            lines.append(f'  <line x1="{cx - pilot_offset - 2}" y1="{cy}" x2="{cx - pilot_offset + 2}" y2="{cy}" stroke="blue" stroke-width="0.15"/>')
            lines.append(f'  <line x1="{cx - pilot_offset}" y1="{cy - 2}" x2="{cx - pilot_offset}" y2="{cy + 2}" stroke="blue" stroke-width="0.15"/>')
            lines.append(f'  <line x1="{cx + pilot_offset - 2}" y1="{cy}" x2="{cx + pilot_offset + 2}" y2="{cy}" stroke="blue" stroke-width="0.15"/>')
            lines.append(f'  <line x1="{cx + pilot_offset}" y1="{cy - 2}" x2="{cx + pilot_offset}" y2="{cy + 2}" stroke="blue" stroke-width="0.15"/>')
            # Label
            lines.append(f'  <text x="{cx}" y="{cy - sh/2 - 2}" font-size="3" font-family="sans-serif" '
                         f'text-anchor="middle" fill="red">{label} (2x 8mm drill, file to {sw}x{sh}mm)</text>')
        else:
            r = dia / 2.0
            lines.append(f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="red" stroke-width="0.3"/>')
            # Crosshair
            lines.append(f'  <line x1="{cx-r-1}" y1="{cy}" x2="{cx+r+1}" y2="{cy}" stroke="red" stroke-width="0.15"/>')
            lines.append(f'  <line x1="{cx}" y1="{cy-r-1}" x2="{cx}" y2="{cy+r+1}" stroke="red" stroke-width="0.15"/>')
            # Label
            lines.append(f'  <text x="{cx}" y="{cy - r - 2}" font-size="3" font-family="sans-serif" '
                         f'text-anchor="middle" fill="red">{label} dia {dia}</text>')

    # Edge labels
    lines.append(f'  <text x="{margin - 1}" y="{margin + 15 + strip_height + 4}" '
                 f'font-size="2.5" font-family="sans-serif">bottom edge</text>')
    lines.append(f'  <text x="{margin - 1}" y="{margin + 15 - 2}" '
                 f'font-size="2.5" font-family="sans-serif">top edge (align here)</text>')
    lines.append(f'  <text x="{margin}" y="{margin + 15 + strip_height + 8}" '
                 f'font-size="2" font-family="sans-serif" fill="gray">left = front of case</text>')

    lines.append(f'</g>')
    return lines, w, h


# Generate full SVG with all three strips
svg_parts = []
total_height = 0
max_width = 0

strips = [
    ("Left side (looking from outside)", left_holes, case_width, case_height, None),
    ("Right side (looking from outside)", right_holes, case_width, case_height, None),
    ("Back (looking from outside)", back_holes, case_length, case_height, (usb_width, usb_height_dim)),
]

y_offset = 0
for title, holes, length, height, usb in strips:
    part_lines, w, h = svg_strip(holes, length, height, title, usb_slot=usb)
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
