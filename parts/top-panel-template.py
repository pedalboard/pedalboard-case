#!/usr/bin/env python3
"""
Generate 1:1 printable SVG cutting template for the top panel.

Reads from top-panel-coords.json.

Usage:
    python3 top-panel-template.py --output ../generated/display-cutout-template.svg
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from panel_coords import load_coords, cnc_coords


def parse_args():
    p = argparse.ArgumentParser(description="Generate printable SVG template")
    p.add_argument("--output", type=str, required=True, help="Output SVG file")
    p.add_argument("--coords", type=Path, default=None, help="Coordinates JSON file")
    return p.parse_args()


def main():
    args = parse_args()
    data = load_coords(args.coords)
    coords = cnc_coords(data)
    features = coords["features"]
    case = coords["case"]

    page_w = 297
    page_h = 210
    surface_w = case["top_surface_width"]
    surface_h = case["top_surface_height"]

    margin_x = (page_w - surface_w) / 2
    margin_y = (page_h - surface_h) / 2

    def sx(x): return margin_x + x
    def sy(y): return margin_y + y

    button_dia = features["button_hole_diameter"]
    encoder_dia = features["encoder_hole_diameter"]
    display_w = features["display_cutout_width"]
    display_h = features["display_cutout_height"]
    lightpipe_dia = features["lightpipe_hole_diameter"]
    bezel_dia = features["bezel_hole_diameter"]
    led_ring_od = features["led_ring_outer_diameter"]
    corner_drill = 3.0

    e = []
    e.append(f'<rect width="{page_w}" height="{page_h}" fill="white"/>')
    e.append(f'<text x="{page_w/2}" y="10" text-anchor="middle" font-family="sans-serif" font-size="4.5" font-weight="bold">Pedalboard Case Cutting Template (1:1)</text>')
    e.append(f'<text x="{page_w/2}" y="15" text-anchor="middle" font-family="sans-serif" font-size="2.8" fill="#555">Display cutout: {display_w}×{display_h}mm. Print at 100% on A4.</text>')

    # 50mm ruler
    rx = page_w / 2
    e.append(f'<line x1="{rx-25}" y1="20" x2="{rx+25}" y2="20" stroke="black" stroke-width="0.4"/>')
    e.append(f'<line x1="{rx-25}" y1="18" x2="{rx-25}" y2="22" stroke="black" stroke-width="0.4"/>')
    e.append(f'<line x1="{rx+25}" y1="18" x2="{rx+25}" y2="22" stroke="black" stroke-width="0.4"/>')
    for i in range(1, 5):
        e.append(f'<line x1="{rx-25+i*10}" y1="19" x2="{rx-25+i*10}" y2="21" stroke="black" stroke-width="0.3"/>')
    e.append(f'<text x="{rx}" y="24.5" text-anchor="middle" font-family="sans-serif" font-size="2.5">50 mm</text>')

    # Surface outline
    e.append(f'<rect x="{sx(0)}" y="{sy(0)}" width="{surface_w}" height="{surface_h}" fill="none" stroke="#aaa" stroke-width="0.25" stroke-dasharray="3,2"/>')
    e.append(f'<text x="{sx(surface_w/2)}" y="{sy(-2.5)}" text-anchor="middle" font-family="sans-serif" font-size="2" fill="#aaa">Case surface {surface_w} × {surface_h} mm</text>')

    # Buttons
    for i, (bx, by) in enumerate(coords["buttons"]):
        e.append(f'<circle cx="{sx(bx)}" cy="{sy(by)}" r="{button_dia/2}" fill="none" stroke="red" stroke-width="0.4"/>')
        e.append(f'<circle cx="{sx(bx)}" cy="{sy(by)}" r="{led_ring_od/2}" fill="none" stroke="orange" stroke-width="0.3" stroke-dasharray="1.5,1"/>')
        e.append(f'<circle cx="{sx(bx)}" cy="{sy(by)}" r="0.4" fill="red"/>')
        e.append(f'<text x="{sx(bx)}" y="{sy(by - led_ring_od/2 - 2)}" text-anchor="middle" font-family="sans-serif" font-size="2" fill="red">B{i+1}</text>')

    # Encoders
    for i, (ex, ey) in enumerate(coords["encoders"]):
        e.append(f'<circle cx="{sx(ex)}" cy="{sy(ey)}" r="{encoder_dia/2}" fill="none" stroke="red" stroke-width="0.4"/>')
        e.append(f'<circle cx="{sx(ex)}" cy="{sy(ey)}" r="{led_ring_od/2}" fill="none" stroke="orange" stroke-width="0.3" stroke-dasharray="1.5,1"/>')
        e.append(f'<circle cx="{sx(ex)}" cy="{sy(ey)}" r="0.4" fill="red"/>')
        e.append(f'<text x="{sx(ex)}" y="{sy(ey - led_ring_od/2 - 2)}" text-anchor="middle" font-family="sans-serif" font-size="2" fill="red">E{i+1}</text>')

    # Displays
    for i, (dx, dy) in enumerate(coords["displays"]):
        e.append(f'<rect x="{sx(dx - display_w/2)}" y="{sy(dy - display_h/2)}" width="{display_w}" height="{display_h}" fill="none" stroke="red" stroke-width="0.5"/>')
        for cx, cy in [(-1,-1), (1,-1), (-1,1), (1,1)]:
            e.append(f'<circle cx="{sx(dx + cx*display_w/2)}" cy="{sy(dy + cy*display_h/2)}" r="{corner_drill/2}" fill="none" stroke="blue" stroke-width="0.3"/>')
        e.append(f'<line x1="{sx(dx-4)}" y1="{sy(dy)}" x2="{sx(dx+4)}" y2="{sy(dy)}" stroke="red" stroke-width="0.15"/>')
        e.append(f'<line x1="{sx(dx)}" y1="{sy(dy-4)}" x2="{sx(dx)}" y2="{sy(dy+4)}" stroke="red" stroke-width="0.15"/>')
        e.append(f'<text x="{sx(dx)}" y="{sy(dy - display_h/2 - 3)}" text-anchor="middle" font-family="sans-serif" font-size="2.2" fill="red" font-weight="bold">D{i+1}</text>')

    # Light pipes
    for i, (lx, ly) in enumerate(coords["single_leds"]):
        e.append(f'<circle cx="{sx(lx)}" cy="{sy(ly)}" r="{lightpipe_dia/2}" fill="none" stroke="red" stroke-width="0.4"/>')
        e.append(f'<circle cx="{sx(lx)}" cy="{sy(ly)}" r="0.3" fill="red"/>')
        e.append(f'<text x="{sx(lx)}" y="{sy(ly - lightpipe_dia/2 - 2)}" text-anchor="middle" font-family="sans-serif" font-size="1.8" fill="red">LP{i+1}</text>')

    # Bezel holes
    for i, (hx, hy) in enumerate(coords["bezel_holes"]):
        e.append(f'<circle cx="{sx(hx)}" cy="{sy(hy)}" r="{bezel_dia/2}" fill="none" stroke="green" stroke-width="0.25"/>')

    # Legend
    ly = page_h - 26
    e.append(f'<rect x="12" y="{ly}" width="135" height="22" fill="none" stroke="#ddd" stroke-width="0.2"/>')
    e.append(f'<text x="15" y="{ly+4}" font-family="sans-serif" font-size="2.3" font-weight="bold">Legend</text>')
    e.append(f'<circle cx="18" cy="{ly+8}" r="3" fill="none" stroke="red" stroke-width="0.4"/>')
    e.append(f'<text x="23" y="{ly+9}" font-family="sans-serif" font-size="2">Cut — ø{button_dia} buttons/encoders, {display_w}×{display_h} displays, ø{lightpipe_dia} light pipes</text>')
    e.append(f'<circle cx="18" cy="{ly+12.5}" r="3" fill="none" stroke="orange" stroke-width="0.3" stroke-dasharray="1.5,1"/>')
    e.append(f'<text x="23" y="{ly+13.5}" font-family="sans-serif" font-size="2">LED ring ø{led_ring_od} — washer on top (reference)</text>')
    e.append(f'<circle cx="18" cy="{ly+17}" r="1.5" fill="none" stroke="blue" stroke-width="0.3"/>')
    e.append(f'<text x="23" y="{ly+18}" font-family="sans-serif" font-size="2">Corner drill ø{corner_drill} — for rectangular display cutouts</text>')
    e.append(f'<circle cx="18" cy="{ly+21}" r="0.85" fill="none" stroke="green" stroke-width="0.25"/>')
    e.append(f'<text x="23" y="{ly+22}" font-family="sans-serif" font-size="2">Bezel mount ø{bezel_dia} (M1.6 clearance)</text>')

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{page_w}mm" height="{page_h}mm" 
     viewBox="0 0 {page_w} {page_h}">
  {chr(10).join(e)}
</svg>'''

    with open(args.output, 'w') as f:
        f.write(svg)
    print(f"Written: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
