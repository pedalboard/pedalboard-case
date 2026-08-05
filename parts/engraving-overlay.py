#!/usr/bin/env python3
"""
engraving-overlay.py — Overlay engraving design on cutting template SVG.

Combines the display-cutout-template.svg (hole positions) with the
top-panel-engraving.svg (label positions) so you can visually verify
that labels don't overlap with holes.

Also marks all probe points used by engrave-setup.py:
  - Blue cross: spoilboard Z reference (machine coords, off-panel)
  - Green cross + circle: Z reference probe (work offset +20,0)
  - Cyan dots: height map grid probe points (38 probed, 22 skipped)
  - Grey dots: skipped grid points (over holes)

Usage:
    python3 parts/engraving-overlay.py
    python3 parts/engraving-overlay.py --output generated/engraving-overlay.svg
"""

import argparse
import math
import re
import sys
from pathlib import Path

GENERATED  = Path(__file__).parent.parent / "generated"
TEMPLATE   = GENERATED / "display-cutout-template.svg"
ENGRAVING  = GENERATED / "top-panel-engraving.svg"
OUTPUT     = GENERATED / "engraving-overlay.svg"

# Panel position in the A4 cutting template
PAGE_W, PAGE_H = 297.0, 210.0
PANEL_W, PANEL_H = 181.8, 113.8
MARGIN_X = (PAGE_W - PANEL_W) / 2   # 57.6mm
MARGIN_Y = (PAGE_H - PANEL_H) / 2   # 48.1mm

# Grid parameters (from engrave-setup.py)
# Work coords: X = short axis (±CASE_HALF_WIDTH-margin = ±53.9)
#              Y = long axis  (±CASE_HALF_HEIGHT-margin = ±87.9)
GRID_COLS   = 8
GRID_ROWS   = 7
GRID_X_HALF = PANEL_H / 2 - 3.0   # 53.9mm — short axis (work X = machine X)
GRID_Y_HALF = PANEL_W / 2 - 3.0   # 87.9mm — long axis  (work Y = machine Y)

# Probe tip radius for hole avoidance
PROBE_TIP = 2.0
HOLE_MARGIN = PROBE_TIP + 1.0

# Z reference probe offset from case centre (work coords)
Z_REF_OFFSET_X = 20.0
Z_REF_OFFSET_Y =  0.0

# Panel centre in panel coords (origin=front-left)
PANEL_CX = PANEL_W / 2   # 90.9
PANEL_CY = PANEL_H / 2   # 56.9


def extract_svg_content(path: Path) -> str:
    text = path.read_text()
    text = re.sub(r'<\?xml[^?]*\?>', '', text).strip()
    m = re.search(r'<svg[^>]*>(.*)</svg>', text, re.DOTALL)
    if not m:
        raise ValueError(f"No <svg> content found in {path}")
    return m.group(1).strip()


def build_hole_list() -> list:
    """Return holes in panel coords (origin=front-left, Y=0=front)."""
    sys.path.insert(0, str(Path(__file__).parent))
    sys.path.insert(0, str(Path(__file__).parent.parent / "cnc"))
    from panel_coords import load_coords, cnc_coords

    data   = load_coords(str(Path(__file__).parent / "top-panel-coords.json"))
    # origin=corner gives landscape panel coords directly
    coords = cnc_coords(data, origin="corner", angle_deg=0.0)
    feats  = data["features"]

    # Convert portrait CNC coords to landscape panel coords
    # landscape_x = portrait_cnc_y, landscape_y = PANEL_H - portrait_cnc_x
    H = PANEL_H
    holes = []
    for ox, oy in coords["buttons"]:
        holes.append(("button",  oy, H - ox, feats["button_hole_diameter"]  / 2 + HOLE_MARGIN, None, None))
    for ox, oy in coords["encoders"]:
        holes.append(("encoder", oy, H - ox, feats["encoder_hole_diameter"] / 2 + HOLE_MARGIN, None, None))
    for ox, oy in coords["single_leds"]:
        holes.append(("led",     oy, H - ox, feats["lightpipe_hole_diameter"]/ 2 + HOLE_MARGIN, None, None))
    for ox, oy in coords["bezel_holes"]:
        holes.append(("bezel",   oy, H - ox, feats["bezel_hole_diameter"]   / 2 + HOLE_MARGIN, None, None))
    dw = 42.5 / 2 + HOLE_MARGIN
    dh = feats["display_cutout_height"] / 2 + HOLE_MARGIN
    for ox, oy in coords["displays"]:
        holes.append(("display", oy, H - ox, None, dw, dh))
    return holes


def point_in_hole(px, py, holes) -> bool:
    for _, hx, hy, r, hw, hh in holes:
        if r is not None:
            if math.hypot(px - hx, py - hy) < r:
                return True
        else:
            if abs(px - hx) < hw and abs(py - hy) < hh:
                return True
    return False


def grid_points(holes) -> list:
    """Return list of (panel_x, panel_y, skipped).

    Computes grid in work coords (same as engrave-setup.py), checks holes
    in work coords, then converts to panel display coords for rendering.

    Work coord mapping (from panel_coords origin=center empirical check):
      panel_x = work_y + PANEL_W/2
      panel_y = -work_x + PANEL_H/2
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from panel_coords import load_coords, cnc_coords as _cnc
    _data   = load_coords(str(Path(__file__).parent / "top-panel-coords.json"))
    _feats  = _data["features"]
    _coords = _cnc(_data, origin="center", angle_deg=0.0)

    # Build hole list in work coords (same as engrave-setup._build_hole_list)
    work_holes = []
    for x, y in _coords["buttons"]:
        work_holes.append((x, y, _feats["button_hole_diameter"]  / 2 + HOLE_MARGIN, None, None))
    for x, y in _coords["encoders"]:
        work_holes.append((x, y, _feats["encoder_hole_diameter"] / 2 + HOLE_MARGIN, None, None))
    for x, y in _coords["single_leds"]:
        work_holes.append((x, y, _feats["lightpipe_hole_diameter"]/ 2 + HOLE_MARGIN, None, None))
    for x, y in _coords["bezel_holes"]:
        work_holes.append((x, y, _feats["bezel_hole_diameter"]   / 2 + HOLE_MARGIN, None, None))
    _dw = 42.5 / 2 + HOLE_MARGIN
    _dh = _feats["display_cutout_height"] / 2 + HOLE_MARGIN
    for x, y in _coords["displays"]:
        work_holes.append((x, y, None, _dw, _dh))

    def _in_hole(gx, gy):
        for hx, hy, r, hw, hh in work_holes:
            if r is not None:
                if math.hypot(gx - hx, gy - hy) < r:
                    return True
            else:
                if abs(gx - hx) < hw and abs(gy - hy) < hh:
                    return True
        return False

    xs = [-GRID_X_HALF + i * 2 * GRID_X_HALF / (GRID_COLS - 1) for i in range(GRID_COLS)]
    ys = [-GRID_Y_HALF + j * 2 * GRID_Y_HALF / (GRID_ROWS - 1) for j in range(GRID_ROWS)]

    points = []
    for gy in ys:
        for gx in xs:
            skip = _in_hole(gx, gy)
            # Convert work coords to landscape panel display coords:
            # panel_x = work_y + PANEL_W/2
            # panel_y = -work_x + PANEL_H/2
            px = gy + PANEL_W / 2
            py = -gx + PANEL_H / 2
            points.append((px, py, skip))

    n_probe = sum(1 for _, _, s in points if not s)
    n_skip  = sum(1 for _, _, s in points if s)
    print(f"    Grid: {GRID_COLS}×{GRID_ROWS} = {len(points)} points  "
          f"({n_probe} probed, {n_skip} skipped)")
    return points


def probe_marker(x, y, r, color, label="") -> str:
    """SVG crosshair + circle at panel coords (x,y). r=radius of circle."""
    # SVG Y is flipped: svg_y = PANEL_H - panel_y
    sx, sy = x, PANEL_H - y
    lines = []
    lines.append(f'<circle cx="{sx:.3f}" cy="{sy:.3f}" r="{r:.2f}" '
                 f'fill="none" stroke="{color}" stroke-width="0.4"/>')
    lines.append(f'<line x1="{sx-r*1.5:.3f}" y1="{sy:.3f}" '
                 f'x2="{sx+r*1.5:.3f}" y2="{sy:.3f}" '
                 f'stroke="{color}" stroke-width="0.3"/>')
    lines.append(f'<line x1="{sx:.3f}" y1="{sy-r*1.5:.3f}" '
                 f'x2="{sx:.3f}" y2="{sy+r*1.5:.3f}" '
                 f'stroke="{color}" stroke-width="0.3"/>')
    if label:
        lines.append(f'<text x="{sx+r+0.5:.3f}" y="{sy+1:.3f}" '
                     f'font-family="sans-serif" font-size="2.5" fill="{color}">{label}</text>')
    return "\n    ".join(lines)


def dot(x, y, r, color) -> str:
    # SVG Y is flipped: svg_y = PANEL_H - panel_y
    sx, sy = x, PANEL_H - y
    return (f'<circle cx="{sx:.3f}" cy="{sy:.3f}" r="{r:.2f}" '
            f'fill="{color}" stroke="none"/>')


def parse_args():
    p = argparse.ArgumentParser(description="Overlay engraving design on cutting template")
    p.add_argument("--output",   default=str(OUTPUT))
    p.add_argument("--template", default=str(TEMPLATE))
    p.add_argument("--engraving",default=str(ENGRAVING))
    return p.parse_args()


def main():
    args = parse_args()

    template_content  = extract_svg_content(Path(args.template))
    engraving_content = extract_svg_content(Path(args.engraving))
    engraving_content = re.sub(r'<rect[^/]*/>', '', engraving_content, count=1).strip()

    holes  = build_hole_list()
    points = grid_points(holes)

    n_probed  = sum(1 for _, _, s in points if not s)
    n_skipped = sum(1 for _, _, s in points if s)

    # Z reference probe point: work (+20, 0)
    # panel_x = work_y + PANEL_W/2 = 0 + 90.9 = 90.9
    # panel_y = -work_x + PANEL_H/2 = -20 + 56.9 = 36.9
    z_ref_px = Z_REF_OFFSET_Y + PANEL_W / 2
    z_ref_py = -Z_REF_OFFSET_X + PANEL_H / 2

    # Build probe markers (all in panel coords, rendered inside panel transform)
    probe_svg_parts = []

    # Grid points
    for px, py, skip in points:
        if skip:
            probe_svg_parts.append(dot(px, py, 0.8, "#aaaaaa"))
        else:
            probe_svg_parts.append(dot(px, py, 1.0, "#00aacc"))

    # Z reference probe
    probe_svg_parts.append(probe_marker(z_ref_px, z_ref_py, 2.5, "#00aa00", "Z ref"))

    probe_svg = "\n    ".join(probe_svg_parts)

    legend_items = [
        ("#00aacc", f"Grid probe points ({n_probed} probed)"),
        ("#aaaaaa", f"Skipped — over hole ({n_skipped})"),
        ("#00aa00", "Z reference probe (+20,0)"),
    ]
    legend_svg = ""
    lx = 10.0
    for color, label in legend_items:
        legend_svg += (f'<circle cx="{lx:.1f}" cy="202" r="1.5" fill="{color}"/>'
                       f'<text x="{lx+3:.1f}" y="203" font-family="sans-serif" '
                       f'font-size="2.8" fill="#333">{label}</text>')
        lx += 60.0

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{PAGE_W}mm" height="{PAGE_H}mm"
     viewBox="0 0 {PAGE_W} {PAGE_H}">

  <!-- Cutting template (holes, bezel holes, display cutouts) -->
  {template_content}

  <!-- Engraving labels + probe points overlay -->
  <g transform="translate({MARGIN_X:.3f},{MARGIN_Y:.3f})" opacity="0.85">
    {engraving_content}
  </g>

  <!-- Probe points (same panel transform) -->
  <g transform="translate({MARGIN_X:.3f},{MARGIN_Y:.3f})">
    {probe_svg}
  </g>

  <!-- Legend -->
  <text x="10" y="196" font-family="sans-serif" font-size="2.5" fill="#555">
    Dark brown: engraving labels  |  Red/green circles: hole cuts
  </text>
  {legend_svg}

</svg>'''

    out = Path(args.output)
    out.write_text(svg)
    n_total = GRID_COLS * GRID_ROWS
    print(f"Written: {out}")
    print(f"Grid: {GRID_COLS}×{GRID_ROWS} = {n_total} points  ({n_probed} probed, {n_skipped} skipped)")


if __name__ == "__main__":
    main()
