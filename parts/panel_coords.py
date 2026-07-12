"""
Shared coordinate transformation for top panel outputs.

Reads top-panel-coords.json and provides CNC/drawing coordinates
for all features. Used by G-code, DXF, and SVG generators.
"""

import json
from pathlib import Path


def load_coords(json_path=None):
    """Load coordinates from JSON file."""
    if json_path is None:
        json_path = Path(__file__).parent / "top-panel-coords.json"
    with open(json_path) as f:
        return json.load(f)


def cnc_coords(data):
    """Convert all positions to CNC coordinates.

    Origin: front-left corner of case top flat surface.
    X+ = right, Y+ = toward rear.
    """
    case = data["case"]
    pcb = data["pcb"]
    features = data["features"]
    positions = data["positions"]

    # PCB centered in case top surface
    pcb_offset_x = (case["top_surface_width"] - pcb["width"]) / 2.0
    pcb_offset_y = (case["top_surface_height"] - pcb["height"]) / 2.0

    def to_cnc(kicad_x, kicad_y):
        pcb_x = kicad_x - pcb["kicad_origin_x"]
        pcb_y = kicad_y - pcb["kicad_origin_y"]
        return (pcb_offset_x + pcb_x, pcb_offset_y + pcb_y)

    result = {
        "case": case,
        "features": features,
        "buttons": [to_cnc(p["x"], p["y"]) for p in positions["buttons"]],
        "encoders": [to_cnc(p["x"], p["y"]) for p in positions["encoders"]],
        "displays": [to_cnc(p["x"], p["y"]) for p in positions["displays"]],
        "single_leds": [to_cnc(p["x"], p["y"]) for p in positions["single_leds"]],
        "bezel_holes": [to_cnc(p["x"], p["y"]) for p in positions["bezel_holes"]],
    }
    return result
