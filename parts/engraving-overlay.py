#!/usr/bin/env python3
"""
engraving-overlay.py — Overlay engraving design on cutting template SVG.

Combines the display-cutout-template.svg (hole positions) with the
top-panel-engraving.svg (label positions) so you can visually verify
that labels don't overlap with holes.

Usage:
    python3 parts/engraving-overlay.py
    python3 parts/engraving-overlay.py --output generated/engraving-overlay.svg

The cutting template uses A4 landscape (297×210mm viewBox) with the panel
centered at margin_x=57.6, margin_y=48.1.

The engraving SVG uses panel coordinates directly (181.8×113.8mm viewBox,
Y=0=front, Y=113.8=back). The SVG Y axis is flipped (Y increases downward)
so the front of the case appears at the bottom of the SVG.

To align them, the engraving content is placed inside a <g> transform that:
  1. Translates to the panel origin in the template coordinate system
  2. No rotation needed — both use the same landscape orientation
"""

import argparse
import re
from pathlib import Path

GENERATED  = Path(__file__).parent.parent / "generated"
TEMPLATE   = GENERATED / "display-cutout-template.svg"
ENGRAVING  = GENERATED / "top-panel-engraving.svg"
OUTPUT     = GENERATED / "engraving-overlay.svg"

# Panel position in the A4 cutting template (from top-panel-template.py)
PAGE_W, PAGE_H = 297.0, 210.0
PANEL_W, PANEL_H = 181.8, 113.8
MARGIN_X = (PAGE_W - PANEL_W) / 2   # 57.6mm
MARGIN_Y = (PAGE_H - PANEL_H) / 2   # 48.1mm


def extract_svg_content(path: Path) -> str:
    """Extract everything inside the <svg> tag (strip the outer svg element)."""
    text = path.read_text()
    # Remove XML declaration
    text = re.sub(r'<\?xml[^?]*\?>', '', text).strip()
    # Extract content between <svg ...> and </svg>
    m = re.search(r'<svg[^>]*>(.*)</svg>', text, re.DOTALL)
    if not m:
        raise ValueError(f"No <svg> content found in {path}")
    return m.group(1).strip()


def parse_args():
    p = argparse.ArgumentParser(description="Overlay engraving design on cutting template")
    p.add_argument("--output", default=str(OUTPUT),
                   help=f"Output SVG path (default: {OUTPUT})")
    p.add_argument("--template", default=str(TEMPLATE),
                   help=f"Cutting template SVG (default: {TEMPLATE})")
    p.add_argument("--engraving", default=str(ENGRAVING),
                   help=f"Engraving SVG (default: {ENGRAVING})")
    return p.parse_args()


def main():
    args = parse_args()

    template_content  = extract_svg_content(Path(args.template))
    engraving_content = extract_svg_content(Path(args.engraving))

    # The engraving SVG has a background rect — skip it so template shows through
    # Remove the first <rect> element (background) from engraving content
    engraving_content = re.sub(
        r'<rect[^/]*/>', '', engraving_content, count=1
    ).strip()

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{PAGE_W}mm" height="{PAGE_H}mm"
     viewBox="0 0 {PAGE_W} {PAGE_H}">

  <!-- Cutting template (holes, bezel holes, display cutouts) -->
  {template_content}

  <!-- Engraving labels overlay
       Transform: translate to panel origin in template coords.
       The engraving SVG uses panel coords (0,0)=front-left, same as template panel origin.
  -->
  <g transform="translate({MARGIN_X:.3f},{MARGIN_Y:.3f})"
     opacity="0.85">
    {engraving_content}
  </g>

  <!-- Legend -->
  <text x="10" y="205" font-family="sans-serif" font-size="3" fill="#333">
    Red/green: hole cuts  |  Dark brown: engraving labels  |  Verify no label overlaps a hole
  </text>

</svg>'''

    out = Path(args.output)
    out.write_text(svg)
    print(f"Written: {out}")


if __name__ == "__main__":
    main()
