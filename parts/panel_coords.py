"""
Shared coordinate transformation for top panel outputs.

Reads top-panel-coords.json and provides CNC/drawing coordinates
for all features. Used by G-code, DXF, and SVG generators.
"""

import json
import math
from pathlib import Path


def load_coords(json_path=None):
    """Load coordinates from JSON file."""
    if json_path is None:
        json_path = Path(__file__).parent / "top-panel-coords.json"
    with open(json_path) as f:
        return json.load(f)


def rotate_point(x, y, angle_deg):
    """Rotate (x, y) around origin by angle_deg degrees (CCW positive).

    Used to compensate for case rotation in fixture.
    A positive angle means the case is rotated CCW relative to the
    machine axes — we apply a CW correction to the toolpaths.
    """
    if angle_deg == 0.0:
        return (x, y)
    θ = math.radians(-angle_deg)  # negate: correct for case rotation
    cos_θ = math.cos(θ)
    sin_θ = math.sin(θ)
    return (
        x * cos_θ - y * sin_θ,
        x * sin_θ + y * cos_θ,
    )


def cnc_coords(data, origin="corner", angle_deg=0.0):
    """Convert all positions to CNC coordinates.

    Args:
        data: loaded JSON data
        origin: "corner" — front-left corner of case top flat surface
                "center" — case center (for probe-both-sides workflow)
        angle_deg: fixture rotation angle in degrees (CCW positive).
                   Measured by probing two points on the same edge.
                   Applied as a counter-rotation to all toolpath coordinates.

    Case mounted with long axis along Y, short axis along X.
    PCB layout has long axis as X — we swap X↔Y in the transform.
    X+ = right, Y+ = toward rear. Z=0 = top surface.
    """
    case = data["case"]
    pcb = data["pcb"]
    features = data["features"]
    positions = data["positions"]

    # PCB centered in case top surface
    # Note: PCB "width" is along the long axis (becomes Y on machine)
    #       PCB "height" is along the short axis (becomes X on machine)
    pcb_offset_long = (case["top_surface_width"] - pcb["width"]) / 2.0
    pcb_offset_short = (case["top_surface_height"] - pcb["height"]) / 2.0

    if origin == "center":
        # Origin at case center (probe both sides, compute midpoint)
        def to_cnc(kicad_x, kicad_y):
            pcb_x = kicad_x - pcb["kicad_origin_x"]
            pcb_y = kicad_y - pcb["kicad_origin_y"]
            # Swap: PCB X (long) → CNC Y, PCB Y (short) → CNC X
            cnc_x = pcb_y - pcb["height"] / 2.0
            cnc_y = pcb_x - pcb["width"] / 2.0
            return rotate_point(cnc_x, cnc_y, angle_deg)
    else:
        # Origin at front-left corner of flat surface
        def to_cnc(kicad_x, kicad_y):
            pcb_x = kicad_x - pcb["kicad_origin_x"]
            pcb_y = kicad_y - pcb["kicad_origin_y"]
            # Swap: PCB X (long) → CNC Y, PCB Y (short) → CNC X
            cnc_x = pcb_offset_short + pcb_y
            cnc_y = pcb_offset_long + pcb_x
            return rotate_point(cnc_x, cnc_y, angle_deg)

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
