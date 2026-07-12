#!/usr/bin/env python3
"""
Generate DXF of top panel cutouts for CNC shop.

Reads from top-panel-coords.json. Output is a 2D DXF with all cut
profiles (circles and rectangles) on appropriate layers.

Usage:
    python3 top-panel-dxf.py > top-panel.dxf
    python3 top-panel-dxf.py --output top-panel.dxf
"""

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from panel_coords import load_coords, cnc_coords


def parse_args():
    p = argparse.ArgumentParser(description="Generate DXF for top panel cutouts")
    p.add_argument("--output", type=str, default=None,
                   help="Output file (default: stdout)")
    p.add_argument("--coords", type=Path, default=None,
                   help="Coordinates JSON file")
    return p.parse_args()


class DXF:
    """Minimal DXF writer (no dependencies)."""

    def __init__(self):
        self.entities = []

    def circle(self, cx, cy, radius, layer="CUT"):
        self.entities.append(
            f"0\nCIRCLE\n8\n{layer}\n10\n{cx:.4f}\n20\n{cy:.4f}\n30\n0.0\n40\n{radius:.4f}\n"
        )

    def rect(self, cx, cy, width, height, layer="CUT"):
        """Rectangle as 4 lines (no corner radius)."""
        x1, y1 = cx - width/2, cy - height/2
        x2, y2 = cx + width/2, cy + height/2
        self.line(x1, y1, x2, y1, layer)
        self.line(x2, y1, x2, y2, layer)
        self.line(x2, y2, x1, y2, layer)
        self.line(x1, y2, x1, y1, layer)

    def line(self, x1, y1, x2, y2, layer="CUT"):
        self.entities.append(
            f"0\nLINE\n8\n{layer}\n10\n{x1:.4f}\n20\n{y1:.4f}\n30\n0.0\n"
            f"11\n{x2:.4f}\n21\n{y2:.4f}\n31\n0.0\n"
        )

    def point(self, x, y, layer="DRILL"):
        self.entities.append(
            f"0\nPOINT\n8\n{layer}\n10\n{x:.4f}\n20\n{y:.4f}\n30\n0.0\n"
        )

    def render(self):
        header = (
            "0\nSECTION\n2\nHEADER\n"
            "9\n$INSUNITS\n70\n4\n"  # mm
            "0\nENDSEC\n"
            "0\nSECTION\n2\nTABLES\n"
            "0\nTABLE\n2\nLAYER\n70\n3\n"
            "0\nLAYER\n2\nOUTLINE\n70\n0\n62\n7\n6\nCONTINUOUS\n"
            "0\nLAYER\n2\nCUT\n70\n0\n62\n1\n6\nCONTINUOUS\n"
            "0\nLAYER\n2\nDRILL\n70\n0\n62\n3\n6\nCONTINUOUS\n"
            "0\nENDTAB\n"
            "0\nENDSEC\n"
            "0\nSECTION\n2\nENTITIES\n"
        )
        footer = "0\nENDSEC\n0\nEOF\n"
        return header + "".join(self.entities) + footer


def main():
    args = parse_args()
    data = load_coords(args.coords)
    coords = cnc_coords(data)
    features = coords["features"]
    case = coords["case"]

    dxf = DXF()

    # Case surface outline (reference)
    dxf.rect(case["top_surface_width"]/2, case["top_surface_height"]/2,
             case["top_surface_width"], case["top_surface_height"], "OUTLINE")

    # Button holes
    for x, y in coords["buttons"]:
        dxf.circle(x, y, features["button_hole_diameter"]/2, "CUT")

    # Encoder holes
    for x, y in coords["encoders"]:
        dxf.circle(x, y, features["encoder_hole_diameter"]/2, "CUT")

    # Display cutouts
    for x, y in coords["displays"]:
        dxf.rect(x, y, features["display_cutout_width"],
                 features["display_cutout_height"], "CUT")

    # Light pipe holes
    for x, y in coords["single_leds"]:
        dxf.circle(x, y, features["lightpipe_hole_diameter"]/2, "CUT")

    # Bezel mounting holes
    for x, y in coords["bezel_holes"]:
        dxf.circle(x, y, features["bezel_hole_diameter"]/2, "DRILL")

    output = dxf.render()

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Written: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
