#!/usr/bin/env python3
"""
engrave-setup.py — Surface height map probing for powder-coated panel engraving.

Probes a grid of Z heights across the Hammond 1590DD top panel surface,
skipping all hole positions. Saves a heightmap.json for use with plates.py
--heightmap to compensate for surface variation when engraving.

Workflow:
  1. Home machine
  2. Pause: install 3D probe
  3. Probe spoilboard Z reference
  4. Probe X-, X+, Y-, Y+ edges → case center + rotation angle, set G54 X0 Y0
  5. Probe surface Z at grid points (skipping holes)
  6. Save heightmap.json
  7. Generate engraving.nc via plates.py --heightmap
  8. Pause: remove 3D probe, install V-bit
  9. Probe Z with touch plate, set G54 Z0
  10. Ready to engrave

Usage:
    python3 engrave-setup.py
    python3 engrave-setup.py --dry-run
    python3 engrave-setup.py --port /tmp/cnc-sim   # test with simulator

Preconditions:
    - gSender disconnected (script owns /dev/cnc)
    - Case mounted open-side-down on fixture plate
    - Holes already cut (from probe-setup.py + top-panel.nc run)
    - Machine in idle state
"""

import argparse
import json
import math
import sys
from pathlib import Path

from grbl import (
    HOMING_TIMEOUT,
    GrblConnection,
    check_plausibility,
    pause,
    probe_edge_double,
    probe_spoilboard,
    probe_z_double,
    probe_z_surface,
)

# Add plates project to path (editable install doesn't expose top-level modules)
_PLATES_DIR = Path(__file__).parent / "../../../laenzlinger/plates"
_PLATES_DIR = _PLATES_DIR.resolve()
if _PLATES_DIR.exists() and str(_PLATES_DIR) not in sys.path:
    sys.path.insert(0, str(_PLATES_DIR))

# === MACHINE CONFIGURATION ===

PORT = "/dev/cnc"
BAUD = 115200

SAFE_Z             = 10.0   # mm — safe Z for rapids
GRID_TRAVERSE_Z    =  3.0   # mm — Z above surface for moves between probe points
FEED_FAST          = 100.0  # mm/min
FEED_SLOW          =  20.0  # mm/min
PROBE_TIP_RADIUS   =  2.0   # mm — HLTNC 3D probe tip radius
TOUCH_PLATE_THICKNESS = 19.25  # mm

# Case geometry (machine coords)
CASE_CENTER_X       = 110.0
CASE_CENTER_Y       = 190.0
CASE_HALF_WIDTH     = 113.8 / 2.0   # X half-extent (short axis)
CASE_HALF_HEIGHT    = 181.8 / 2.0   # Y half-extent (long axis)
CASE_HEIGHT_NOMINAL = 33.0           # mm — case wall height open-side-down
XY_PROBE_BELOW_SURFACE = 5.0

APPROACH_CLEARANCE  = 20.0
PROBE_TRAVEL_Z      = 80.0

ANGLE_PROBE_Y_FRONT = CASE_CENTER_Y - 60.0
ANGLE_PROBE_Y_BACK  = CASE_CENTER_Y + 60.0

TOOL_CHANGE_X = 110.0
TOOL_CHANGE_Y = 5.0

SPOILBOARD_PROBE_X = 10.0
SPOILBOARD_PROBE_Y = 190.0

# Plausibility tolerances
EXPECTED_CASE_WIDTH  = 113.8
EXPECTED_CASE_HEIGHT = 181.8
MAX_WIDTH_ERROR  = 10.0
MAX_ANGLE_DEG    =  5.0
MAX_CENTER_ERROR = 30.0

# === GRID CONFIGURATION ===

# 3mm margin from each edge (inside the 1mm fillet radius + clearance)
GRID_MARGIN = 3.0

# Grid in G54 work coordinates (origin = case centre)
# Panel: 181.8 (Y long) x 113.8 (X short) → half-extents minus margin
GRID_X_HALF = CASE_HALF_WIDTH  - GRID_MARGIN   # 53.9mm
GRID_Y_HALF = CASE_HALF_HEIGHT - GRID_MARGIN   # 87.9mm

# ~20mm spacing → 6 cols x 10 rows = 60 points (38 probed after hole avoidance)
GRID_COLS = 7
GRID_ROWS = 8

# Hole avoidance: probe tip radius + 1mm safety margin
_HOLE_MARGIN = PROBE_TIP_RADIUS + 1.0   # 3.0mm extra

# Paths
SCRIPT_DIR     = Path(__file__).parent
REPO_ROOT      = SCRIPT_DIR.parent
ENGRAVING_YAML = REPO_ROOT / "parts" / "top-panel-engraving.yaml"
HEIGHTMAP_FILE = REPO_ROOT / "heightmap.json"
ENGRAVING_NC   = REPO_ROOT / "engraving.nc"
COORDS_JSON    = REPO_ROOT / "parts" / "top-panel-coords.json"


# === HOLE AVOIDANCE ===

def _build_hole_list(angle_deg: float) -> list:
    """Return list of (type, cx, cy, radius_or_None, half_w_or_None, half_h_or_None).

    All coordinates in G54 work coords (origin at case centre, Y+ = toward back).
    Applies angle correction to match the probed case orientation.

    Coordinate conversion from panel_coords (origin=corner, landscape):
      work_x = panel_x - PANEL_W/2
      work_y = panel_y - PANEL_H/2   (panel Y=0=front, work Y- = front)
    """
    sys.path.insert(0, str(REPO_ROOT / "parts"))
    from panel_coords import load_coords, cnc_coords

    data   = load_coords(str(COORDS_JSON))
    # Use origin=corner to get landscape panel coords, then convert to work coords
    coords = cnc_coords(data, origin="corner", angle_deg=angle_deg)
    feats  = data["features"]

    PANEL_W = data["case"]["top_surface_width"]   # 181.8
    PANEL_H = data["case"]["top_surface_height"]  # 113.8

    def to_work(px, py):
        """Panel coords (origin=front-left, landscape) -> work coords (G54, origin=centre).

        Empirically verified (from panel_coords origin=center cross-check):
          work_x = -(panel_y - PANEL_H/2)   (machine X = short axis = panel Y direction)
          work_y =   panel_x - PANEL_W/2    (machine Y = long axis  = panel X direction)
        """
        return -(py - PANEL_H / 2), px - PANEL_W / 2

    holes = []

    # Circular holes — convert landscape panel coords to work coords
    for ox, oy in coords["buttons"]:
        # coords["buttons"] gives (portrait_cnc_x, portrait_cnc_y)
        # landscape: panel_x = portrait_cnc_y, panel_y = PANEL_H - portrait_cnc_x
        panel_x, panel_y = oy, PANEL_H - ox
        wx, wy = to_work(panel_x, panel_y)
        holes.append(("button", wx, wy,
                      feats["button_hole_diameter"] / 2 + _HOLE_MARGIN, None, None))
    for ox, oy in coords["encoders"]:
        panel_x, panel_y = oy, PANEL_H - ox
        wx, wy = to_work(panel_x, panel_y)
        holes.append(("encoder", wx, wy,
                      feats["encoder_hole_diameter"] / 2 + _HOLE_MARGIN, None, None))
    for ox, oy in coords["single_leds"]:
        panel_x, panel_y = oy, PANEL_H - ox
        wx, wy = to_work(panel_x, panel_y)
        holes.append(("led", wx, wy,
                      feats["lightpipe_hole_diameter"] / 2 + _HOLE_MARGIN, None, None))
    for ox, oy in coords["bezel_holes"]:
        panel_x, panel_y = oy, PANEL_H - ox
        wx, wy = to_work(panel_x, panel_y)
        holes.append(("bezel", wx, wy,
                      feats["bezel_hole_diameter"] / 2 + _HOLE_MARGIN, None, None))

    # Rectangular display cutouts
    dw = 42.5 / 2 + _HOLE_MARGIN
    dh = feats["display_cutout_height"] / 2 + _HOLE_MARGIN
    for ox, oy in coords["displays"]:
        panel_x, panel_y = oy, PANEL_H - ox
        wx, wy = to_work(panel_x, panel_y)
        holes.append(("display", wx, wy, None, dw, dh))

    return holes


def _point_in_hole(gx: float, gy: float, holes: list) -> bool:
    """Return True if (gx, gy) is inside any hole's avoidance zone."""
    for _, hx, hy, r, hw, hh in holes:
        if r is not None:
            if math.hypot(gx - hx, gy - hy) < r:
                return True
        else:
            if abs(gx - hx) < hw and abs(gy - hy) < hh:
                return True
    return False


def build_grid(angle_deg: float) -> tuple:
    """Build the probe grid, returning (xs, ys, grid_points, holes).

    grid_points: list of (col, row, x, y, skip) where skip=True means in a hole.
    xs, ys: the column/row coordinate arrays.
    """
    xs = [round(-GRID_X_HALF + i * 2 * GRID_X_HALF / (GRID_COLS - 1), 4)
          for i in range(GRID_COLS)]
    ys = [round(-GRID_Y_HALF + j * 2 * GRID_Y_HALF / (GRID_ROWS - 1), 4)
          for j in range(GRID_ROWS)]

    holes = _build_hole_list(angle_deg)

    points = []
    for row, gy in enumerate(ys):
        for col, gx in enumerate(xs):
            skip = _point_in_hole(gx, gy, holes)
            points.append((col, row, gx, gy, skip))

    n_probe  = sum(1 for _, _, _, _, s in points if not s)
    n_skip   = sum(1 for _, _, _, _, s in points if s)
    print(f"    Grid: {GRID_COLS}×{GRID_ROWS} = {len(points)} points  "
          f"({n_probe} probed, {n_skip} skipped over holes)")

    return xs, ys, points, holes


# === MAIN ===

def run(args):
    grbl = GrblConnection(args.port, BAUD, dry_run=args.dry_run)

    try:
        # [1] Check machine state
        print("\n[1/9] Checking machine state...")
        if not args.dry_run and args.port == PORT:
            result = subprocess.run(["pgrep", "-f", "gsender"], capture_output=True)
            if result.returncode == 0:
                print("ERROR: gSender is running. Close it first.", file=sys.stderr)
                sys.exit(1)
        grbl.check_state()

        # [2] Home
        print("\n[2/9] Homing machine (Z first for safety)...")
        try:
            grbl.send("$X", timeout=5)
        except (RuntimeError, TimeoutError):
            pass
        grbl.send("$HZ", timeout=HOMING_TIMEOUT)
        grbl.send("$HX", timeout=HOMING_TIMEOUT)
        grbl.send("$HY", timeout=HOMING_TIMEOUT)

        grbl.send("G53 G0 Z0")
        grbl.send(f"G53 G0 X{TOOL_CHANGE_X} Y{TOOL_CHANGE_Y}")
        pause("Install 3D probe (HLTNC). Ensure probe is connected.",
              dry_run=args.dry_run)
        grbl.send("G90")
        grbl.send("G53 G0 Z0")
        print("\n    Checking probe...")
        grbl.confirm_probe_trigger(
            "Touch the 3D probe tip to confirm it triggers.",
            dry_run=args.dry_run)

        # [3] Spoilboard probe
        print("\n[3/9] Probing spoilboard reference surface...")
        spoilboard_z = probe_spoilboard(
            grbl,
            x=SPOILBOARD_PROBE_X, y=SPOILBOARD_PROBE_Y,
            safe_z=SAFE_Z, travel=PROBE_TRAVEL_Z,
        )
        grbl.send("G53 G0 Z0")

        # [4] XY edge probing
        print("\n[4/9] Probing case edges for center and angle...")
        xy_probe_z = spoilboard_z + CASE_HEIGHT_NOMINAL - XY_PROBE_BELOW_SURFACE
        print(f"    XY probe Z: {xy_probe_z:.3f}mm")

        grbl.send(f"G53 G0 X{CASE_CENTER_X - CASE_HALF_WIDTH - APPROACH_CLEARANCE:.3f} Y{ANGLE_PROBE_Y_FRONT:.3f}")
        grbl.send(f"G53 G0 Z{xy_probe_z:.3f}")
        x_minus_front = probe_edge_double(grbl, "X", +1, "X- edge (front)")
        grbl.send("G53 G0 Z0")

        grbl.send(f"G53 G0 X{CASE_CENTER_X - CASE_HALF_WIDTH - APPROACH_CLEARANCE:.3f} Y{ANGLE_PROBE_Y_BACK:.3f}")
        grbl.send(f"G53 G0 Z{xy_probe_z:.3f}")
        x_minus_back = probe_edge_double(grbl, "X", +1, "X- edge (back)")
        grbl.send("G53 G0 Z0")

        grbl.send(f"G53 G0 X{CASE_CENTER_X + CASE_HALF_WIDTH + APPROACH_CLEARANCE:.3f} Y{CASE_CENTER_Y:.3f}")
        grbl.send(f"G53 G0 Z{xy_probe_z:.3f}")
        x_plus = probe_edge_double(grbl, "X", -1, "X+ edge")
        grbl.send("G53 G0 Z0")

        grbl.send(f"G53 G0 X{CASE_CENTER_X:.3f} Y{CASE_CENTER_Y - CASE_HALF_HEIGHT - APPROACH_CLEARANCE:.3f}")
        grbl.send(f"G53 G0 Z{xy_probe_z:.3f}")
        y_minus = probe_edge_double(grbl, "Y", +1, "Y- edge")
        grbl.send("G53 G0 Z0")

        grbl.send(f"G53 G0 X{CASE_CENTER_X:.3f} Y{CASE_CENTER_Y + CASE_HALF_HEIGHT + APPROACH_CLEARANCE:.3f}")
        grbl.send(f"G53 G0 Z{xy_probe_z:.3f}")
        y_plus = probe_edge_double(grbl, "Y", -1, "Y+ edge")
        grbl.send("G53 G0 Z0")

        # [5] Compute center and angle, set G54
        print("\n[5/9] Computing center and angle...")
        x_minus_avg = (x_minus_front + x_minus_back) / 2.0
        center_x    = (x_minus_avg + x_plus) / 2.0
        center_y    = (y_minus + y_plus) / 2.0
        dy          = ANGLE_PROBE_Y_BACK - ANGLE_PROBE_Y_FRONT
        dx          = x_minus_back - x_minus_front
        angle_deg   = math.degrees(math.atan2(dx, dy))

        print(f"    Case center: X={center_x:.4f} Y={center_y:.4f}")
        print(f"    Rotation angle: {angle_deg:.4f}°")

        if not args.dry_run:
            if x_minus_avg >= x_plus:
                raise RuntimeError(
                    f"X- edge ({x_minus_avg:.4f}) is not left of X+ ({x_plus:.4f}).")
            measured_width = abs(x_plus - x_minus_avg) - 2 * PROBE_TIP_RADIUS
            check_plausibility("case X width",   measured_width, EXPECTED_CASE_WIDTH,  MAX_WIDTH_ERROR)
            check_plausibility("case center X",  center_x,       CASE_CENTER_X,        MAX_CENTER_ERROR)
            check_plausibility("case center Y",  center_y,       CASE_CENTER_Y,        MAX_CENTER_ERROR)
            check_plausibility("rotation angle", angle_deg,      0.0,                  MAX_ANGLE_DEG)
            print("    Plausibility checks passed ✓")

        grbl.send(f"G53 G0 X{center_x:.3f} Y{center_y:.3f}")
        grbl.send("G10 L20 P1 X0 Y0")
        print("    G54 X0 Y0 set at case centre")

        # [6] Reference surface Z
        # Default offset (+20, 0): avoids the E button hole at centre (r=11.15mm).
        # 10mm clearance from nearest hole edge.
        if args.z_probe_offset:
            z_probe_x = center_x + args.z_probe_offset[0]
            z_probe_y = center_y + args.z_probe_offset[1]
            print(f"\n[6/9] Probing reference surface Z at offset ({args.z_probe_offset[0]}, {args.z_probe_offset[1]})...")
        else:
            z_probe_x = center_x + 20.0
            z_probe_y = center_y + 0.0
            print("\n[6/9] Probing reference surface Z at offset (+20, 0) (avoids centre button hole)...")
        grbl.send("G53 G0 Z0")
        grbl.send(f"G53 G0 X{z_probe_x:.3f} Y{z_probe_y:.3f}")
        grbl.send(f"G53 G0 Z-{SAFE_Z:.3f}")
        surface_z_ref = probe_z_surface(grbl, travel=PROBE_TRAVEL_Z)
        grbl.send("G53 G0 Z0")

        if not args.dry_run:
            case_height = surface_z_ref - spoilboard_z
            print(f"    Measured case height: {case_height:.3f}mm (expected {CASE_HEIGHT_NOMINAL}mm)")
            check_plausibility("case height", case_height, CASE_HEIGHT_NOMINAL, 5.0)

        # [7] Height map grid probing
        print("\n[7/9] Building surface height map...")
        print(f"    Building probe grid (angle={angle_deg:.4f}°)...")
        xs, ys, grid_points, holes = build_grid(angle_deg)

        # Grid: rows×cols array of Z offsets relative to surface_z_ref
        # Initialise with zeros; fill in probed values; skip = nearest neighbour fill later
        grid_data = [[0.0] * GRID_COLS for _ in range(GRID_ROWS)]
        probed    = [[False] * GRID_COLS for _ in range(GRID_ROWS)]

        # Z height for traversing between probe points: 3mm above reference surface
        traverse_z_machine = surface_z_ref + GRID_TRAVERSE_Z

        probe_count = 0
        for col, row, gx, gy, skip in grid_points:
            if skip:
                continue

            # Move to probe point in G54 work coords
            # First lateral move at traverse height, then probe
            grbl.send(f"G53 G0 Z{traverse_z_machine:.3f}")
            grbl.send(f"G90 G0 X{gx:.3f} Y{gy:.3f}")

            # Probe Z — only need ~10mm travel from traverse height
            grbl.send("G91")
            fast_result = grbl.probe(f"G38.2 Z-10.000 F{FEED_FAST}")
            grbl.send("G0 Z2.0")
            slow_result = grbl.probe(f"G38.2 Z-5.000 F{FEED_SLOW}")
            grbl.send("G90")

            point_z  = slow_result[2]
            z_offset = point_z - surface_z_ref
            grid_data[row][col] = round(z_offset, 4)
            probed[row][col]    = True
            probe_count += 1
            print(f"    [{probe_count:2d}] ({col},{row}) X={gx:+6.1f} Y={gy:+6.1f}  "
                  f"Z={point_z:.4f}  offset={z_offset:+.4f}mm")

        grbl.send("G53 G0 Z0")

        # Fill skipped grid points by nearest probed neighbour
        # (bilinear interpolation in HeightMap handles intermediate values;
        # we just need a reasonable value at each grid cell so the JSON is complete)
        print("\n    Filling skipped grid points by nearest-neighbour...")
        for col, row, gx, gy, skip in grid_points:
            if not skip:
                continue
            best_dist = float("inf")
            best_z    = 0.0
            for c2, r2, gx2, gy2, s2 in grid_points:
                if s2:
                    continue
                d = math.hypot(gx - gx2, gy - gy2)
                if d < best_dist:
                    best_dist = d
                    best_z    = grid_data[r2][c2]
            grid_data[row][col] = best_z

        # Save heightmap.json
        heightmap = {
            "x_min": xs[0],
            "x_max": xs[-1],
            "y_min": ys[0],
            "y_max": ys[-1],
            "cols":  GRID_COLS,
            "rows":  GRID_ROWS,
            "grid":  grid_data,
        }
        if not args.dry_run:
            HEIGHTMAP_FILE.write_text(json.dumps(heightmap, indent=2))
            print(f"    Saved: {HEIGHTMAP_FILE}")

        z_vals = [grid_data[r][c] for r in range(GRID_ROWS) for c in range(GRID_COLS)]
        print(f"    Z offset range: {min(z_vals):+.4f} .. {max(z_vals):+.4f} mm")

        # [8] Generate engraving G-code
        print("\n[8/9] Generating engraving G-code...")
        if not args.dry_run:
            import plates as plates_mod
            import config as plates_config
            import preview as plates_preview

            print(f"    Loading {ENGRAVING_YAML}...")
            conf = plates_config.load(str(ENGRAVING_YAML))

            # Apply angle to all features — plates uses origin=corner by default
            # but the engraving YAML uses landscape coords already baked in.
            # We just need to pass the heightmap.
            hm_data = json.loads(HEIGHTMAP_FILE.read_text())
            from toolpath.heightmap import HeightMap
            heightmap = HeightMap(
                x_min=hm_data["x_min"], x_max=hm_data["x_max"],
                y_min=hm_data["y_min"], y_max=hm_data["y_max"],
                grid=hm_data["grid"],
            )
            print(f"    Height map: {heightmap.rows}×{heightmap.cols} points  "
                  f"max deviation {heightmap.max_deviation:.3f}mm")

            layouts = plates_preview.resolve_layouts(conf)
            gcode   = plates_mod.generate_gcode(conf, layouts, heightmap=heightmap)
            errors  = plates_mod.validate_gcode(gcode)
            if errors:
                print("ERROR: G-code validation failed:", file=sys.stderr)
                for e in errors:
                    print(f"  {e}", file=sys.stderr)
                sys.exit(1)
            ENGRAVING_NC.write_text(gcode)
            print(f"    Written: {ENGRAVING_NC}")
        else:
            print("    [dry-run: skipping G-code generation]")

        # [9] Tool change: remove 3D probe, install V-bit
        print("\n[9/9] Tool change and Z probe...")
        grbl.send(f"G53 G0 X{TOOL_CHANGE_X} Y{TOOL_CHANGE_Y}")
        pause("Remove 3D probe. Install V-bit.", dry_run=args.dry_run)

        grbl.send("G53 G0 Z0")
        grbl.send(f"G53 G0 X{z_probe_x:.3f} Y{z_probe_y:.3f}")
        grbl.send(f"G53 G0 Z-{SAFE_Z:.3f}")
        pause(
            f"Place touch plate ({TOUCH_PLATE_THICKNESS}mm) on workpiece. "
            "Clip ground wire to V-bit.",
            dry_run=args.dry_run)
        print("\n    Checking touch plate...")
        grbl.confirm_probe_trigger(
            "Touch the V-bit to the touch plate to confirm circuit.",
            dry_run=args.dry_run)

        probe_z_double(grbl, travel=PROBE_TRAVEL_Z)
        grbl.send(f"G10 L20 P1 Z{TOUCH_PLATE_THICKNESS:.3f}")
        print(f"    G54 Z0 set (touch plate: {TOUCH_PLATE_THICKNESS}mm)")
        grbl.send("G53 G0 Z0")
        pause("Remove touch plate and ground wire.", dry_run=args.dry_run)

        print("\n" + "=" * 60)
        print("  ENGRAVE SETUP COMPLETE")
        print(f"  Angle:        {angle_deg:.4f}°")
        print(f"  Z range:      {min(z_vals):+.4f} .. {max(z_vals):+.4f} mm")
        print(f"  Height map:   {HEIGHTMAP_FILE}")
        print(f"  Engraving NC: {ENGRAVING_NC}")
        print("=" * 60)
        print(f"\n  Next: open gSender, connect, load and run:")
        print(f"    {ENGRAVING_NC}")

    except Exception as e:
        print(f"\n{'!' * 60}", file=sys.stderr)
        print(f"  ERROR: {e}", file=sys.stderr)
        print(f"  Sending feed hold...", file=sys.stderr)
        grbl.feed_hold()
        print(f"  Machine is in Hold state. Re-run to start over.", file=sys.stderr)
        print(f"{'!' * 60}", file=sys.stderr)
        sys.exit(1)
    finally:
        grbl.close()


def parse_args():
    p = argparse.ArgumentParser(
        description="Surface height map probing for engraving setup")
    p.add_argument("--port", default=PORT,
                   help=f"Serial port (default: {PORT})")
    p.add_argument("--dry-run", action="store_true",
                   help="Print commands without connecting to machine")
    p.add_argument("--z-probe-offset", type=float, nargs=2, default=None,
                   metavar=("X", "Y"),
                   help="Work coords offset from case centre for reference Z probe. "
                        "Default: (+20, 0) — solid surface clear of centre button hole. "
                        "Override if that spot is also cut through.")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args)
