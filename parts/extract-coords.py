#!/usr/bin/env python3
"""
Extract component positions from pedalboard-display KiCad PCB.

Generates top-panel-coords.json — the single source of truth for all
case machining outputs (G-code, DXF, SVG template, drill jig).

Usage:
    python3 extract-coords.py --pcb ../pedalboard-display/pedalboard-display.kicad_pcb
    python3 extract-coords.py  # uses default relative path
"""

import argparse
import json
import re
import sys
from pathlib import Path


DEFAULT_PCB = Path(__file__).parent.parent.parent / "pedalboard-display" / "pedalboard-display.kicad_pcb"


def parse_args():
    p = argparse.ArgumentParser(description="Extract component positions from KiCad PCB")
    p.add_argument("--pcb", type=Path, default=DEFAULT_PCB,
                   help=f"Path to pedalboard-display PCB file (default: {DEFAULT_PCB})")
    p.add_argument("--output", type=Path, default=Path(__file__).parent / "top-panel-coords.json",
                   help="Output JSON file")
    return p.parse_args()


def extract_footprints(pcb_path):
    """Extract footprint positions from KiCad PCB file."""
    with open(pcb_path, 'r') as f:
        content = f.read()

    lines = content.split('\n')
    components = []
    current_fp = None

    for line in lines:
        m = re.match(r'\t\(footprint "([^"]+)"', line)
        if m:
            current_fp = m.group(1)
        elif current_fp and re.match(r'\t\t\(at ', line):
            at_match = re.match(r'\t\t\(at ([\d.]+) ([\d.]+)(?:\s+([\d.-]+))?\)', line)
            if at_match:
                x, y = float(at_match.group(1)), float(at_match.group(2))
                rot = float(at_match.group(3)) if at_match.group(3) else 0.0
                components.append({"footprint": current_fp, "x": x, "y": y, "rotation": rot})
            current_fp = None

    return components


def classify_components(components):
    """Classify components into buttons, encoders, displays, LEDs."""
    buttons = []
    encoders = []
    displays = []
    single_leds = []

    # Known centers for LED ring detection
    button_centers = []
    encoder_centers = []

    for c in components:
        fp = c["footprint"]
        if "Actuator" in fp and "Rotary" not in fp:
            buttons.append({"x": c["x"], "y": c["y"]})
            button_centers.append((c["x"], c["y"]))
        elif "ActuatorRotary" in fp:
            encoders.append({"x": c["x"], "y": c["y"]})
            encoder_centers.append((c["x"], c["y"]))
        elif "OLED" in fp:
            displays.append({"x": c["x"], "y": c["y"]})

    # Find single LEDs (SK6812 not near any button/encoder center)
    all_centers = button_centers + encoder_centers
    for c in components:
        if "SK6812" in c["footprint"]:
            is_ring = False
            for cx, cy in all_centers:
                dist = ((c["x"] - cx)**2 + (c["y"] - cy)**2)**0.5
                if dist < 15:
                    is_ring = True
                    break
            if not is_ring:
                single_leds.append({"x": c["x"], "y": c["y"]})

    return buttons, encoders, displays, single_leds


def main():
    args = parse_args()

    if not args.pcb.exists():
        print(f"ERROR: PCB file not found: {args.pcb}", file=sys.stderr)
        sys.exit(1)

    components = extract_footprints(args.pcb)
    buttons, encoders, displays, single_leds = classify_components(components)

    # Sort for consistent output
    buttons.sort(key=lambda c: (c["x"], c["y"]))
    encoders.sort(key=lambda c: (c["x"], c["y"]))
    displays.sort(key=lambda c: (c["x"], c["y"]))
    single_leds.sort(key=lambda c: (c["x"], c["y"]))

    # Case geometry (from Hammond 1590DD STEP model)
    case = {
        "model": "Hammond 1590DD",
        "top_surface_width": 181.8,
        "top_surface_height": 113.8,
        "bottom_plate_thickness": 2.5,
        "outer_width": 188.0,
        "outer_height": 120.0,
    }

    # PCB geometry
    pcb = {
        "width": 174.0,
        "height": 111.0,
        "kicad_origin_x": 20.0,
        "kicad_origin_y": 25.0,
    }

    # Feature dimensions (from footprints and OpenSCAD models)
    features = {
        "button_hole_diameter": 22.3,
        "encoder_hole_diameter": 22.3,
        "display_cutout_width": 34.5,
        "display_cutout_height": 36.7,
        "lightpipe_hole_diameter": 6.0,
        "bezel_hole_diameter": 4.0,
        "bezel_hole_offset_x": 15.0,
        "bezel_hole_offset_y": 26.0,
        "led_ring_outer_diameter": 24.0,
    }

    # Compute bezel hole positions from display centers
    bezel_holes = []
    for d in displays:
        for sx in [-1, 1]:
            for sy in [-1, 1]:
                bezel_holes.append({
                    "x": d["x"] + sx * features["bezel_hole_offset_x"],
                    "y": d["y"] + sy * features["bezel_hole_offset_y"],
                })

    output = {
        "_comment": "Auto-generated from pedalboard-display KiCad PCB. Do not edit manually.",
        "_source": str(args.pcb),
        "case": case,
        "pcb": pcb,
        "features": features,
        "positions": {
            "buttons": buttons,
            "encoders": encoders,
            "displays": displays,
            "single_leds": single_leds,
            "bezel_holes": bezel_holes,
        },
    }

    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Extracted: {len(buttons)} buttons, {len(encoders)} encoders, "
          f"{len(displays)} displays, {len(single_leds)} single LEDs, "
          f"{len(bezel_holes)} bezel holes", file=sys.stderr)
    print(f"Written: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
