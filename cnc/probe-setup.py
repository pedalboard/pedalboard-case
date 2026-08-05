#!/usr/bin/env python3
"""
probe-setup.py — Full CNC setup for pedalboard case top panel.

Workflow:
  1. Home machine
  2. Pause: install 3D probe
  3. Probe spoilboard Z reference
  4. Probe X-, X+, Y-, Y+ edges to find case center and rotation angle
  5. Set G54 X0 Y0 at case center
  6. Probe case top surface Z with 3D probe
  7. Probe Z at each feature center (buttons, encoders, displays, LEDs)
  8. Pause: remove 3D probe, install cutting tool
  9. Probe Z with touch plate, set G54 Z0
  10. Generate top-panel.nc with angle + Z offsets

Usage:
    python3 probe-setup.py
    python3 probe-setup.py --port /dev/ttyUSB0
    python3 probe-setup.py --dry-run

    # Rework (case already has holes — skip feature probing):
    python3 probe-setup.py --skip-feature-probing --z-probe-offset 10 0

Preconditions:
    - gSender must be disconnected (script owns the serial port)
    - Case mounted open-side-down, centered on spoilboard
    - Machine in idle state (not alarmed)
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

from grbl import (
    FEED_FAST,
    FEED_SLOW,
    HOMING_TIMEOUT,
    GrblConnection,
    check_plausibility,
    pause,
    probe_edge_double,
    probe_spoilboard,
    probe_z_double,
    probe_z_surface,
)

# === MACHINE CONFIGURATION ===

PORT = "/dev/cnc"
BAUD = 115200

SAFE_Z          = 10.0   # mm — safe Z for rapids
FEED_FAST       = 100.0  # mm/min — fast probe feed  (override grbl.py default)
FEED_SLOW       =  20.0  # mm/min — slow probe feed

PROBE_TIP_RADIUS       = 2.0    # mm — HLTNC 3D probe tip radius
TOUCH_PLATE_THICKNESS  = 19.25  # mm

# Case geometry (Hammond 1590DD, long axis along Y in machine coords)
CASE_CENTER_X      = 110.0
CASE_CENTER_Y      = 190.0
CASE_HALF_WIDTH    = 113.8 / 2.0   # X half-extent (short axis)
CASE_HALF_HEIGHT   = 181.8 / 2.0   # Y half-extent (long axis)
CASE_HEIGHT_NOMINAL = 33.0          # mm — case wall height (open-side-down)
XY_PROBE_BELOW_SURFACE = 5.0        # mm — probe this far below case top for XY edges

APPROACH_CLEARANCE = 20.0   # mm — outside case edge before probing
PROBE_TRAVEL_Z     = 80.0   # mm — max Z probe travel

# Two Y positions for angle measurement (along the long X- edge)
ANGLE_PROBE_Y_FRONT = CASE_CENTER_Y - 60.0
ANGLE_PROBE_Y_BACK  = CASE_CENTER_Y + 60.0

TOOL_CHANGE_X = 110.0
TOOL_CHANGE_Y = 5.0

SPOILBOARD_PROBE_X = 10.0
SPOILBOARD_PROBE_Y = 190.0

# Plausibility tolerances
EXPECTED_CASE_WIDTH  = 113.8
EXPECTED_CASE_HEIGHT = 181.8
MAX_WIDTH_ERROR      = 10.0
MAX_ANGLE_DEG        = 5.0
MAX_CENTER_ERROR     = 30.0

# Paths
SCRIPT_DIR     = Path(__file__).parent
REPO_ROOT      = SCRIPT_DIR.parent
GCODE_GENERATOR = REPO_ROOT / "parts" / "top-panel-gcode.py"
GCODE_OUTPUT   = REPO_ROOT / "top-panel.nc"
Z_OFFSETS_FILE = REPO_ROOT / "z-offsets.json"


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
        pause("Install 3D probe (HLTNC). Ensure probe is connected to probe input.",
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

        # [5] Compute center and angle
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
                    f"X- edge ({x_minus_avg:.4f}) is not left of X+ edge ({x_plus:.4f}).")
            measured_width = abs(x_plus - x_minus_avg) - 2 * PROBE_TIP_RADIUS
            check_plausibility("case X width",   measured_width, EXPECTED_CASE_WIDTH,  MAX_WIDTH_ERROR)
            check_plausibility("case center X",  center_x,       CASE_CENTER_X,        MAX_CENTER_ERROR)
            check_plausibility("case center Y",  center_y,       CASE_CENTER_Y,        MAX_CENTER_ERROR)
            check_plausibility("rotation angle", angle_deg,      0.0,                  MAX_ANGLE_DEG)
            print("    Plausibility checks passed ✓")
        else:
            print("    Plausibility checks skipped (dry-run)")

        grbl.send(f"G53 G0 X{center_x:.3f} Y{center_y:.3f}")
        grbl.send("G10 L20 P1 X0 Y0")

        if not args.dry_run:
            g54 = grbl.read_g54()
            if g54 is None:
                print("    WARNING: G54 readback failed")
            else:
                print(f"    G54 readback: X={g54[0]:.4f} Y={g54[1]:.4f} Z={g54[2]:.4f} ✓")
        print("    G54 X0 Y0 set at case center")

        # [6] Z surface probe
        if args.z_probe_offset:
            z_probe_x = center_x + args.z_probe_offset[0]
            z_probe_y = center_y + args.z_probe_offset[1]
            print(f"\n[6/9] Probing case top at offset ({args.z_probe_offset[0]}, {args.z_probe_offset[1]})...")
        else:
            z_probe_x = center_x
            z_probe_y = center_y
            print("\n[6/9] Probing case top surface at center...")

        grbl.send("G53 G0 Z0")
        grbl.send(f"G53 G0 X{z_probe_x:.3f} Y{z_probe_y:.3f}")
        grbl.send(f"G53 G0 Z-{SAFE_Z:.3f}")
        surface_z_machine = probe_z_surface(grbl, travel=PROBE_TRAVEL_Z)
        grbl.send("G53 G0 Z0")

        if not args.dry_run:
            case_height = surface_z_machine - spoilboard_z
            print(f"    Measured case height: {case_height:.3f}mm (expected {CASE_HEIGHT_NOMINAL}mm)")
            check_plausibility("case height", case_height, CASE_HEIGHT_NOMINAL, 5.0)

        # [6b] Per-feature Z probing
        if args.skip_feature_probing:
            print("\n[6b/9] Skipping per-feature Z probing (reusing existing z-offsets.json)")
        else:
            print("\n[6b/9] Probing Z at each feature center...")
            sys.path.insert(0, str(REPO_ROOT / "parts"))
            from panel_coords import load_coords, cnc_coords
            panel_data   = load_coords(str(REPO_ROOT / "parts" / "top-panel-coords.json"))
            panel_coords = cnc_coords(panel_data, origin="center", angle_deg=angle_deg)

            feature_groups = [
                ("single_leds", panel_coords["single_leds"]),
                ("buttons",     panel_coords["buttons"]),
                ("encoders",    panel_coords["encoders"]),
                ("displays",    panel_coords["displays"]),
            ]

            z_offsets       = {}
            feature_probe_z = surface_z_machine + 3.0   # 3mm above case top

            for group_name, positions in feature_groups:
                offsets = []
                for i, (fx, fy) in enumerate(positions):
                    grbl.send(f"G53 G0 Z{feature_probe_z:.3f}")
                    grbl.send(f"G90 G0 X{fx:.3f} Y{fy:.3f}")
                    grbl.send("G91")
                    grbl.probe(f"G38.2 Z-10.000 F{FEED_FAST}")
                    grbl.send("G0 Z2.0")
                    slow_result = grbl.probe(f"G38.2 Z-5.000 F{FEED_SLOW}")
                    grbl.send("G90")
                    feature_z = slow_result[2]
                    offset    = feature_z - surface_z_machine
                    offsets.append(round(offset, 3))
                    print(f"    {group_name}[{i}]: Z={feature_z:.3f} offset={offset:.3f}mm")
                z_offsets[group_name] = offsets

            if not args.dry_run:
                Z_OFFSETS_FILE.write_text(json.dumps(z_offsets, indent=2))
                print(f"    Saved Z offsets to {Z_OFFSETS_FILE}")

        grbl.send("G53 G0 Z0")

        # [7] Tool change
        print("\n[7/9] Moving to tool change position...")
        grbl.send(f"G53 G0 X{TOOL_CHANGE_X} Y{TOOL_CHANGE_Y}")
        pause("Remove 3D probe. Install cutting tool (4mm single flute).",
              dry_run=args.dry_run)

        # [8] Z probe with touch plate
        print("\n[8/9] Probing Z with touch plate...")
        grbl.send("G53 G0 Z0")
        grbl.send(f"G53 G0 X{z_probe_x:.3f} Y{z_probe_y:.3f}")
        grbl.send(f"G53 G0 Z-{SAFE_Z:.3f}")
        pause(
            f"Place touch plate ({TOUCH_PLATE_THICKNESS}mm) on workpiece. "
            "Clip ground wire to cutting tool.",
            dry_run=args.dry_run)
        print("\n    Checking touch plate...")
        grbl.confirm_probe_trigger(
            "Touch the cutting tool to the touch plate to confirm circuit.",
            dry_run=args.dry_run)

        cutting_tool_z = probe_z_double(grbl, travel=PROBE_TRAVEL_Z)
        grbl.send(f"G10 L20 P1 Z{TOUCH_PLATE_THICKNESS:.3f}")
        print(f"    G54 Z0 set (touch plate: {TOUCH_PLATE_THICKNESS}mm)")
        grbl.send("G53 G0 Z0")
        pause("Remove touch plate and ground wire.", dry_run=args.dry_run)

        # [9] Generate G-code
        print("\n[9/9] Generating G-code...")
        cmd = [
            sys.executable,
            str(GCODE_GENERATOR),
            "--origin", "center",
            "--angle", f"{angle_deg:.4f}",
            "--z-offsets", str(Z_OFFSETS_FILE),
        ]
        if args.skip_feature_probing:
            cmd.append("--displays-only")
        print(f"    Running: {' '.join(cmd)}")
        if not args.dry_run:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"ERROR generating G-code:\n{result.stderr}", file=sys.stderr)
                sys.exit(1)
            GCODE_OUTPUT.write_text(result.stdout)
            print(f"    Written: {GCODE_OUTPUT}")

        print("\n" + "=" * 60)
        print("  SETUP COMPLETE")
        print(f"  Angle: {angle_deg:.4f}°")
        print(f"  G-code: {GCODE_OUTPUT}")
        print("=" * 60)
        print(f"\n  Next: open gSender, connect, load and run:")
        print(f"    {GCODE_OUTPUT}")

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
    p = argparse.ArgumentParser(description="Probe setup for pedalboard case top panel")
    p.add_argument("--port", default=PORT,
                   help=f"Serial port (default: {PORT})")
    p.add_argument("--dry-run", action="store_true",
                   help="Print commands without connecting to machine")
    p.add_argument("--skip-feature-probing", action="store_true",
                   help="Skip per-feature Z probing (reuse existing z-offsets.json)")
    p.add_argument("--z-probe-offset", type=float, nargs=2, default=None,
                   metavar=("X", "Y"),
                   help="Work coords for Z surface probe (default: case center). "
                        "Use when center has a hole from previous cuts.")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args)
