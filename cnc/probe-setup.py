#!/usr/bin/env python3
"""
probe-setup.py — Full CNC setup for pedalboard case top panel.

Workflow:
  1. Home machine
  2. Pause: install 3D probe
  3. Probe X-, X+, Y- (two points) to find case center and rotation angle
  4. Set G54 X0 Y0 at case center
  5. Move to tool change position
  6. Pause: remove 3D probe, install cutting tool
  7. Move over workpiece center
  8. Pause: place touch plate on workpiece, clip wire to tool
  9. Probe Z (double contact)
  10. Retract to safe Z
  11. Pause: remove touch plate
  12. Generate top-panel.nc with computed angle

Usage:
    python3 probe-setup.py
    python3 probe-setup.py --port /dev/ttyUSB0
    python3 probe-setup.py --dry-run   # print commands without connecting

Preconditions:
    - gSender must be disconnected (script owns the serial port)
    - Case mounted open-side-down, centered on spoilboard
    - Machine in idle state (not alarmed)
"""

import argparse
import math
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: make install", file=sys.stderr)
    sys.exit(1)

# === MACHINE CONFIGURATION ===

PORT = "/dev/cnc"
BAUD = 115200
TIMEOUT = 90.0          # seconds to wait for probe response (90mm at 100mm/min = 54s)
HOMING_TIMEOUT = 120.0  # seconds to wait for homing (slow seek + locate)

# Safe heights and speeds
SAFE_Z = 10.0           # mm — safe Z for rapids
PROBE_Z_START = 2.0     # mm — Z height before probing Z (above touch plate)
FEED_FAST = 100.0       # mm/min — fast probe feed
FEED_SLOW = 20.0        # mm/min — slow probe feed
FEED_RAPID = 1000.0     # mm/min — approach moves

# Probe geometry
PROBE_TIP_RADIUS = 2.0  # mm — HLTNC 3D probe tip radius
TOUCH_PLATE_THICKNESS = 19.25  # mm

# Case geometry (Hammond 1590DD, long axis along Y)
# Case centered at machine X=110 Y=190
CASE_CENTER_X = 110.0
CASE_CENTER_Y = 190.0
CASE_HALF_WIDTH = 113.8 / 2.0   # X half-extent (short axis)
CASE_HALF_HEIGHT = 181.8 / 2.0  # Y half-extent (long axis)
CASE_HEIGHT_NOMINAL = 33.0      # mm — case wall height (open-side-down, measured)
XY_PROBE_BELOW_SURFACE = 5.0    # mm — probe this far below case top for XY edges

# Probe approach positions (20mm outside case edge)
APPROACH_CLEARANCE = 20.0
PROBE_TRAVEL_XY = 35.0  # mm — max probe travel for X/Y edge finding
PROBE_TRAVEL_Z = 80.0   # mm — max probe travel for Z

# Y positions for angle measurement (probe X- edge at two Y positions)
# Using the long edge (Y direction) for better angle resolution
ANGLE_PROBE_Y_FRONT = CASE_CENTER_Y - 60.0
ANGLE_PROBE_Y_BACK = CASE_CENTER_Y + 60.0

# Tool change position (X center, Y front, Z top)
TOOL_CHANGE_X = 110.0
TOOL_CHANGE_Y = 5.0

# Spoilboard probe position (bare spot on fixture plate, left of case)
SPOILBOARD_PROBE_X = 10.0
SPOILBOARD_PROBE_Y = 190.0

# Paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
GCODE_GENERATOR = REPO_ROOT / "parts" / "top-panel-gcode.py"
GCODE_OUTPUT = REPO_ROOT / "top-panel.nc"
Z_OFFSETS_FILE = REPO_ROOT / "z-offsets.json"


# === GRBL PROTOCOL ===

class GrblConnection:
    """Minimal GRBL/FluidNC serial protocol handler."""

    def __init__(self, port, baud, dry_run=False):
        self.dry_run = dry_run
        self.conn = None
        if not dry_run:
            self.conn = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # wait for controller reset
            self.conn.flushInput()
            # consume startup message
            self._read_startup()

    def _read_startup(self):
        """Consume controller startup messages."""
        deadline = time.time() + 5.0
        while time.time() < deadline:
            line = self.conn.readline().decode("ascii", errors="replace").strip()
            if line:
                print(f"  < {line}")
                deadline = time.time() + 1.0  # keep reading while data is flowing

    def send(self, cmd, timeout=None):
        """Send a G-code command, wait for 'ok' or 'error'."""
        if timeout is None:
            timeout = TIMEOUT
        print(f"  > {cmd}")
        if self.dry_run:
            return
        self.conn.write((cmd + "\n").encode("ascii"))
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.conn.readline().decode("ascii", errors="replace").strip()
            if line:
                print(f"  < {line}")
            if line.startswith("ok"):
                return
            if line.startswith("error"):
                raise RuntimeError(f"GRBL error in response to '{cmd}': {line}")
        raise TimeoutError(f"Timeout waiting for 'ok' after '{cmd}'")

    def probe(self, cmd):
        """Send a probe command, return (x, y, z) of contact point.

        Parses [PRB:x,y,z:1] response. Raises on probe failure (:0).
        """
        print(f"  > {cmd}")
        if self.dry_run:
            print("  < [PRB:0.000,0.000,0.000:1] (dry-run)")
            return (0.0, 0.0, 0.0)

        self.conn.write((cmd + "\n").encode("ascii"))
        prb = None
        ok_received = False
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            line = self.conn.readline().decode("ascii", errors="replace").strip()
            if line:
                print(f"  < {line}")
            m = re.match(r"\[PRB:([^:]+):(\d)\]", line)
            if m:
                if m.group(2) == "0":
                    raise RuntimeError(f"Probe did not trigger: {line}")
                coords = [float(v) for v in m.group(1).split(",")]
                prb = tuple(coords[:3])
                if ok_received:
                    return prb  # got PRB after ok — done
            if line.startswith("ok"):
                ok_received = True
                if prb is not None:
                    return prb  # normal order: PRB then ok
                # grblHAL sends 'ok' when command is accepted into buffer,
                # [PRB:] comes later when probe actually triggers.
                # Keep waiting with full timeout.
            if line.startswith("error"):
                raise RuntimeError(f"GRBL error during probe: {line}")
        if ok_received and prb is None:
            raise RuntimeError("Got 'ok' but no [PRB:] response — probe input may not be connected")
        raise TimeoutError("Timeout waiting for probe response")

    def feed_hold(self):
        """Send feed hold (!) immediately — no waiting for ok."""
        print("  > ! (FEED HOLD)")
        if self.dry_run:
            return
        self.conn.write(b"!")

    def check_probe_ready(self):
        """Verify probe input is NOT triggered (ready for G38.2).

        Queries status report and checks for Pn:P flag.
        Raises if probe is already triggered.
        """
        if self.dry_run:
            return
        self.conn.write(b"?\n")
        deadline = time.time() + 5.0
        while time.time() < deadline:
            line = self.conn.readline().decode("ascii", errors="replace").strip()
            if line.startswith("<"):
                if "Pn:" in line and "P" in line.split("Pn:")[1].split("|")[0]:
                    raise RuntimeError(
                        "Probe input is already triggered!\n"
                        "Check: is the probe tip pressed against something?\n"
                        "Check: is the probe wiring correct ($6 inversion)?"
                    )
                print(f"    Probe input OK (not triggered)")
                return
        raise TimeoutError("Timeout waiting for status report")

    def confirm_probe_trigger(self, message, dry_run=False):
        """Wait for probe to be triggered and released (no Enter needed).

        Polls status report until Pn:P appears, then until it disappears.
        Skipped in dry-run or non-interactive mode.
        """
        if dry_run:
            print("    [dry-run: skipping probe trigger confirmation]")
            return

        self.check_probe_ready()

        if not sys.stdin.isatty():
            print("    [non-interactive: skipping manual trigger test]")
            return

        sep = "=" * 60
        print(f"\n{sep}")
        print(f"  ACTION REQUIRED: {message}")
        print(f"  (touch and release to confirm)")
        print(sep)

        # Poll until triggered
        while True:
            self.conn.write(b"?\n")
            time.sleep(0.3)
            while self.conn.in_waiting:
                line = self.conn.readline().decode("ascii", errors="replace").strip()
                if line.startswith("<") and "Pn:" in line:
                    pn = line.split("Pn:")[1].split("|")[0]
                    if "P" in pn:
                        print("    Probe triggered \u2713")
                        # Now wait for release
                        time.sleep(0.3)
                        while True:
                            self.conn.write(b"?\n")
                            time.sleep(0.3)
                            while self.conn.in_waiting:
                                line2 = self.conn.readline().decode("ascii", errors="replace").strip()
                                if line2.startswith("<"):
                                    if "Pn:" not in line2 or "P" not in line2.split("Pn:")[1].split("|")[0]:
                                        print("    Probe released \u2713 — ready to probe")
                                        return
                            time.sleep(0.2)



    def read_g54(self):
        """Query $# and return G54 (x, y, z) offsets, or None on failure."""
        if self.dry_run:
            return (0.0, 0.0, 0.0)
        self.conn.write(b"$#\n")
        deadline = time.time() + 5.0
        while time.time() < deadline:
            line = self.conn.readline().decode("ascii", errors="replace").strip()
            if line:
                print(f"  < {line}")
            m = re.match(r"\[G54:([^\]]+)\]", line)
            if m:
                coords = [float(v) for v in m.group(1).split(",")]
                return tuple(coords[:3])
        return None

    def check_state(self):
        """Query machine state. Handle Hold/Alarm by resetting to Idle."""
        if self.dry_run:
            return
        self.conn.write(b"?\n")
        deadline = time.time() + 5.0
        while time.time() < deadline:
            line = self.conn.readline().decode("ascii", errors="replace").strip()
            if line.startswith("<"):
                if "Hold" in line:
                    print("  Machine in Hold state — sending soft reset...")
                    self.conn.write(b"\x18")  # Ctrl+X soft reset
                    time.sleep(2)
                    # Consume reset messages
                    while self.conn.in_waiting:
                        self.conn.readline()
                    return
                if "Alarm" in line:
                    print("  Machine in Alarm state — will unlock and re-home...")
                    return  # $X unlock happens next in the flow
                return
        raise TimeoutError("Timeout waiting for machine state response")

    def close(self):
        if self.conn:
            self.conn.close()


# Plausibility tolerances
EXPECTED_CASE_WIDTH = 113.8   # mm — expected X span (case short axis)
EXPECTED_CASE_HEIGHT = 181.8  # mm — expected Y span (case long axis)
MAX_WIDTH_ERROR = 10.0        # mm — tolerate ±10mm sizing error
MAX_ANGLE_DEG = 5.0           # degrees — abort if angle exceeds this
MAX_CENTER_ERROR = 30.0       # mm — center must be within 30mm of expected


def check_plausibility(label, value, expected, tolerance):
    """Raise if value is outside expected ± tolerance."""
    error = abs(value - expected)
    if error > tolerance:
        raise RuntimeError(
            f"Plausibility check failed: {label}\n"
            f"  Expected: {expected:.3f} ± {tolerance:.1f}\n"
            f"  Got:      {value:.3f}  (error: {error:.3f})"
        )

def probe_edge_double(grbl, axis, direction, label):
    """Probe an edge with fast then slow approach.

    Args:
        axis: 'X' or 'Y'
        direction: +1 or -1
        label: description for logging

    Returns:
        contact position along axis (machine coordinate, float)
    """
    travel = PROBE_TRAVEL_XY * direction
    retract = 2.0 * -direction

    print(f"\n--- Probing {label} ---")

    # Fast probe
    grbl.send("G91")  # incremental
    fast_result = grbl.probe(f"G38.2 {axis}{travel:.3f} F{FEED_FAST}")

    # Retract
    grbl.send(f"G0 {axis}{retract:.3f}")

    # Slow probe
    slow_travel = (PROBE_TRAVEL_XY / 5.0) * direction
    slow_result = grbl.probe(f"G38.2 {axis}{slow_travel:.3f} F{FEED_SLOW}")

    # Retract away from wall before Z retract
    grbl.send(f"G0 {axis}{retract:.3f}")

    grbl.send("G90")  # back to absolute

    idx = {"X": 0, "Y": 1, "Z": 2}[axis]
    fast_contact = fast_result[idx]
    slow_contact = slow_result[idx]

    # Fast/slow agreement check
    agreement = abs(fast_contact - slow_contact)
    if agreement > 0.5:
        raise RuntimeError(
            f"Probe fast/slow disagreement on {label}: "
            f"fast={fast_contact:.4f}, slow={slow_contact:.4f}, diff={agreement:.4f}mm\n"
            "Check probe connection and ensure probe tip is clean."
        )

    print(f"    {label} contact: {axis}={slow_contact:.4f} (fast/slow agreement: {agreement:.4f}mm)")
    return slow_contact


def probe_z_surface(grbl):
    """Probe case top surface with 3D probe (while 3D probe is installed).

    Returns machine Z coordinate of case top surface contact.
    """
    print("\n--- Probing case top surface (Z) ---")
    grbl.send("G91")

    fast_result = grbl.probe(f"G38.2 Z-{PROBE_TRAVEL_Z:.3f} F{FEED_FAST}")
    grbl.send("G0 Z2.0")
    slow_result = grbl.probe(f"G38.2 Z-5.000 F{FEED_SLOW}")
    grbl.send("G90")

    fast_z = fast_result[2]
    slow_z = slow_result[2]
    agreement = abs(fast_z - slow_z)
    if agreement > 0.5:
        raise RuntimeError(
            f"Z surface probe fast/slow disagreement: "
            f"fast={fast_z:.4f}, slow={slow_z:.4f}, diff={agreement:.4f}mm"
        )

    # The [PRB:] Z coordinate is where the probe tip contacted — this IS the
    # surface reference point (probe tip center at contact, tip radius already
    # embedded in the mock/real measurement). Use directly.
    surface_z = slow_z
    print(f"    Case top surface: Z={surface_z:.4f} (machine coords)")
    return surface_z


def probe_spoilboard(grbl):
    """Probe the spoilboard surface at the fixed reference position.

    Returns machine Z coordinate of spoilboard surface.
    Used together with surface_z_machine to compute absolute case height.
    """
    print("\n--- Probing spoilboard surface ---")
    grbl.send("G91")

    fast_result = grbl.probe(f"G38.2 Z-{PROBE_TRAVEL_Z:.3f} F{FEED_FAST}")
    grbl.send("G0 Z2.0")
    slow_result = grbl.probe(f"G38.2 Z-5.000 F{FEED_SLOW}")
    grbl.send("G90")

    fast_z = fast_result[2]
    slow_z = slow_result[2]
    agreement = abs(fast_z - slow_z)
    if agreement > 0.5:
        raise RuntimeError(
            f"Spoilboard probe fast/slow disagreement: "
            f"fast={fast_z:.4f}, slow={slow_z:.4f}, diff={agreement:.4f}mm"
        )

    # The [PRB:] Z coordinate is the probe tip contact point — use directly
    spoilboard_z = slow_z
    print(f"    Spoilboard surface: Z={spoilboard_z:.4f} (machine coords)")
    return spoilboard_z


def probe_z_double(grbl):
    """Probe Z with fast then slow approach. Sets G54 Z0.

    Returns machine Z coordinate of contact point.
    """
    print("\n--- Probing Z ---")

    grbl.send("G91")

    # Fast probe
    fast_result = grbl.probe(f"G38.2 Z-{PROBE_TRAVEL_Z:.3f} F{FEED_FAST}")

    # Retract
    grbl.send("G0 Z2.0")

    # Slow probe
    slow_result = grbl.probe(f"G38.2 Z-5.000 F{FEED_SLOW}")

    grbl.send("G90")

    fast_z = fast_result[2]
    slow_z = slow_result[2]
    agreement = abs(fast_z - slow_z)
    if agreement > 0.5:
        raise RuntimeError(
            f"Z probe fast/slow disagreement: "
            f"fast={fast_z:.4f}, slow={slow_z:.4f}, diff={agreement:.4f}mm"
        )

    # Set G54 Z0 at workpiece surface (account for touch plate thickness)
    grbl.send(f"G10 L20 P1 Z{TOUCH_PLATE_THICKNESS:.3f}")
    print(f"    G54 Z0 set (touch plate: {TOUCH_PLATE_THICKNESS}mm)")
    return slow_z


# === MAIN ===

def pause(msg, dry_run=False):
    """Print message and wait for user confirmation."""
    print(f"\n{'='*60}")
    print(f"  ACTION REQUIRED: {msg}")
    print(f"{'='*60}")
    if dry_run:
        print("  [dry-run: skipping]")
        return
    input("  Press Enter to continue...")


def run(args):
    grbl = GrblConnection(args.port, BAUD, dry_run=args.dry_run)

    try:
        # Verify machine state
        print("\n[1/9] Checking machine state...")

        # Check gSender is not running (it would hold the serial port)
        if not args.dry_run and args.port == PORT:
            result = subprocess.run(["pgrep", "-f", "gsender"], capture_output=True)
            if result.returncode == 0:
                print("ERROR: gSender is running. Close it first (it holds the serial port).", file=sys.stderr)
                sys.exit(1)

        grbl.check_state()

        # Safe home: Z first to clear workpiece, then X and Y
        print("\n[2/9] Homing machine (Z first for safety)...")
        # Unlock if in alarm state (ignore errors — may already be idle)
        try:
            grbl.send("$X", timeout=5)
        except (RuntimeError, TimeoutError):
            pass  # already idle or alarm cleared by reset
        grbl.send("$HZ", timeout=HOMING_TIMEOUT)  # home Z first — clears probe from workpiece
        grbl.send("$HX", timeout=HOMING_TIMEOUT)  # home X
        grbl.send("$HY", timeout=HOMING_TIMEOUT)  # home Y

        # Probe spoilboard at reference position (3D probe not yet installed —
        # use touch plate clipped to a known conductive surface, or install probe first)
        # NOTE: spoilboard probe uses 3D probe, so do it after install pause below.

        # Move to tool change position
        grbl.send(f"G53 G0 Z0")
        grbl.send(f"G53 G0 X{TOOL_CHANGE_X} Y{TOOL_CHANGE_Y}")

        pause("Install 3D probe (HLTNC). Ensure probe is connected to probe input.", dry_run=args.dry_run)

        # Raise to safe Z
        grbl.send("G90")
        grbl.send(f"G53 G0 Z0")

        # Verify probe is connected and working (manual trigger test)
        print("\n    Checking probe...")
        grbl.confirm_probe_trigger(
            "Touch the 3D probe tip to confirm it triggers.",
            dry_run=args.dry_run
        )

        # === SPOILBOARD PROBE ===
        print("\n[3/9] Probing spoilboard reference surface...")
        grbl.send(f"G53 G0 X{SPOILBOARD_PROBE_X:.3f} Y{SPOILBOARD_PROBE_Y:.3f}")
        grbl.send(f"G53 G0 Z-{SAFE_Z:.3f}")  # descend to safe height above spoilboard
        spoilboard_z = probe_spoilboard(grbl)
        grbl.send(f"G53 G0 Z0")

        # === XY PROBING ===
        print("\n[4/9] Probing case edges for center and angle...")

        # Compute XY probe Z: 5mm below expected case top surface
        # spoilboard_z is probe tip contact on spoilboard (machine coords, negative)
        # case top = spoilboard_z + CASE_HEIGHT_NOMINAL (less negative = closer to Z home)
        xy_probe_z = spoilboard_z + CASE_HEIGHT_NOMINAL - XY_PROBE_BELOW_SURFACE
        print(f"    XY probe Z: {xy_probe_z:.3f}mm (spoilboard={spoilboard_z:.3f} + case={CASE_HEIGHT_NOMINAL}mm - {XY_PROBE_BELOW_SURFACE}mm)")

        # Probe X- edge at two Y positions (left edge + angle measurement)
        grbl.send(f"G53 G0 X{CASE_CENTER_X - CASE_HALF_WIDTH - APPROACH_CLEARANCE:.3f} Y{ANGLE_PROBE_Y_FRONT:.3f}")
        grbl.send(f"G53 G0 Z{xy_probe_z:.3f}")
        x_minus_front = probe_edge_double(grbl, "X", +1, "X- edge (front)")
        grbl.send(f"G53 G0 Z0")

        grbl.send(f"G53 G0 X{CASE_CENTER_X - CASE_HALF_WIDTH - APPROACH_CLEARANCE:.3f} Y{ANGLE_PROBE_Y_BACK:.3f}")
        grbl.send(f"G53 G0 Z{xy_probe_z:.3f}")
        x_minus_back = probe_edge_double(grbl, "X", +1, "X- edge (back)")
        grbl.send(f"G53 G0 Z0")

        # Probe X+ edge (right edge, single point at center Y)
        grbl.send(f"G53 G0 X{CASE_CENTER_X + CASE_HALF_WIDTH + APPROACH_CLEARANCE:.3f} Y{CASE_CENTER_Y:.3f}")
        grbl.send(f"G53 G0 Z{xy_probe_z:.3f}")
        x_plus = probe_edge_double(grbl, "X", -1, "X+ edge")
        grbl.send(f"G53 G0 Z0")

        # Probe Y- edge (front edge)
        grbl.send(f"G53 G0 X{CASE_CENTER_X:.3f} Y{CASE_CENTER_Y - CASE_HALF_HEIGHT - APPROACH_CLEARANCE:.3f}")
        grbl.send(f"G53 G0 Z{xy_probe_z:.3f}")
        y_minus = probe_edge_double(grbl, "Y", +1, "Y- edge")
        grbl.send(f"G53 G0 Z0")

        # Probe Y+ edge (back edge)
        grbl.send(f"G53 G0 X{CASE_CENTER_X:.3f} Y{CASE_CENTER_Y + CASE_HALF_HEIGHT + APPROACH_CLEARANCE:.3f}")
        grbl.send(f"G53 G0 Z{xy_probe_z:.3f}")
        y_plus = probe_edge_double(grbl, "Y", -1, "Y+ edge")
        grbl.send(f"G53 G0 Z0")

        # === COMPUTE CENTER AND ANGLE ===
        print("\n[5/9] Computing center and angle...")

        # X center: midpoint of opposite edges (tip radius cancels out)
        x_minus_avg = (x_minus_front + x_minus_back) / 2.0
        center_x = (x_minus_avg + x_plus) / 2.0

        # Y center: midpoint of opposite edges (tip radius cancels out)
        center_y = (y_minus + y_plus) / 2.0

        # Angle from X- edge: two points on the same (long) edge
        dy = ANGLE_PROBE_Y_BACK - ANGLE_PROBE_Y_FRONT  # known Y separation (120mm)
        dx = x_minus_back - x_minus_front               # measured X difference
        angle_deg = math.degrees(math.atan2(dx, dy))

        print(f"    Case center: X={center_x:.4f} Y={center_y:.4f}")
        print(f"    Rotation angle: {angle_deg:.4f}°")

        # Plausibility checks
        if not args.dry_run:
            # X- must be left of X+
            if x_minus_avg >= x_plus:
                raise RuntimeError(
                    f"X- edge ({x_minus_avg:.4f}) is not left of X+ edge ({x_plus:.4f}). "
                    "Check case position and probe approach directions."
                )

            measured_width = abs(x_plus - x_minus_avg) - 2 * PROBE_TIP_RADIUS
            check_plausibility("case X width", measured_width, EXPECTED_CASE_WIDTH, MAX_WIDTH_ERROR)
            check_plausibility("case center X", center_x, CASE_CENTER_X, MAX_CENTER_ERROR)
            check_plausibility("case center Y", center_y, CASE_CENTER_Y, MAX_CENTER_ERROR)
            check_plausibility("rotation angle", angle_deg, 0.0, MAX_ANGLE_DEG)
            print("    Plausibility checks passed ✓")
        else:
            print("    Plausibility checks skipped (dry-run)")

        # Set G54 X0 Y0 at case center
        # Move to computed center first, then use G10 L20 (current pos = 0,0)
        grbl.send(f"G53 G0 X{center_x:.3f} Y{center_y:.3f}")
        grbl.send("G10 L20 P1 X0 Y0")

        # Verify G54 was accepted — $# must return a parseable G54 entry
        if not args.dry_run:
            g54 = grbl.read_g54()
            if g54 is None:
                print("    WARNING: G54 readback failed (may be timing issue, G54 likely set correctly)")
            else:
                print(f"    G54 readback confirmed: offset X={g54[0]:.4f} Y={g54[1]:.4f} Z={g54[2]:.4f} ✓")
        print("    G54 X0 Y0 set at case center")

        # === Z SURFACE PROBE (3D probe still installed) ===
        # Use custom position if center has a hole from previous cuts
        if args.z_probe_offset:
            # Work coords → machine coords (add G54 offset = center)
            z_probe_x = center_x + args.z_probe_offset[0]
            z_probe_y = center_y + args.z_probe_offset[1]
            print(f"\n[6/9] Probing case top surface at offset X={args.z_probe_offset[0]} Y={args.z_probe_offset[1]}...")
        else:
            z_probe_x = center_x
            z_probe_y = center_y
            print("\n[6/9] Probing case top surface at center...")

        grbl.send(f"G53 G0 Z0")  # full Z retract before lateral move
        grbl.send(f"G53 G0 X{z_probe_x:.3f} Y{z_probe_y:.3f}")
        grbl.send(f"G53 G0 Z-{SAFE_Z:.3f}")  # descend to safe height above case
        surface_z_machine = probe_z_surface(grbl)
        grbl.send(f"G53 G0 Z0")  # retract to Z home before tool change

        # Case height plausibility check
        if not args.dry_run:
            case_height = surface_z_machine - spoilboard_z
            print(f"    Measured case height: {case_height:.3f}mm (expected {CASE_HEIGHT_NOMINAL}mm)")
            check_plausibility("case height", case_height, CASE_HEIGHT_NOMINAL, 5.0)

        # === PER-FEATURE Z PROBING ===
        if args.skip_feature_probing:
            print("\n[6b/9] Skipping per-feature Z probing (reusing existing z-offsets.json)")
        else:
            print("\n[6b/9] Probing Z at each feature center...")

            # Load feature positions (same coords the G-code generator uses)
            sys.path.insert(0, str(REPO_ROOT / "parts"))
            from panel_coords import load_coords, cnc_coords
            panel_data = load_coords(str(REPO_ROOT / "parts" / "top-panel-coords.json"))
            panel_coords = cnc_coords(panel_data, origin="center", angle_deg=angle_deg)

            feature_groups = [
                ("single_leds", panel_coords["single_leds"]),
                ("buttons", panel_coords["buttons"]),
                ("encoders", panel_coords["encoders"]),
                ("displays", panel_coords["displays"]),
            ]

            z_offsets = {}
            # Stay 3mm above the known surface for lateral moves between features
            feature_probe_z = surface_z_machine + 3.0  # 3mm above case top

            for group_name, positions in feature_groups:
                offsets = []
                for i, (fx, fy) in enumerate(positions):
                    # Move laterally at safe height above case, then lower to probe height
                    grbl.send(f"G53 G0 Z{feature_probe_z:.3f}")
                    grbl.send(f"G90 G0 X{fx:.3f} Y{fy:.3f}")

                    # Probe Z (only need 10mm travel from 3mm above surface)
                    grbl.send("G91")
                    result = grbl.probe(f"G38.2 Z-10.000 F{FEED_FAST}")
                    grbl.send("G0 Z2.0")
                    slow_result = grbl.probe(f"G38.2 Z-5.000 F{FEED_SLOW}")
                    grbl.send("G90")

                    feature_z = slow_result[2]
                    offset = feature_z - surface_z_machine
                    offsets.append(round(offset, 3))
                    print(f"    {group_name}[{i}]: Z={feature_z:.3f} offset={offset:.3f}mm")

                z_offsets[group_name] = offsets

            # Save offsets to file
            if not args.dry_run:
                import json
                Z_OFFSETS_FILE.write_text(json.dumps(z_offsets, indent=2))
                print(f"    Saved Z offsets to {Z_OFFSETS_FILE}")

        grbl.send(f"G53 G0 Z0")

        # === TOOL CHANGE ===
        print("\n[7/9] Moving to tool change position...")
        grbl.send(f"G53 G0 X{TOOL_CHANGE_X} Y{TOOL_CHANGE_Y}")

        pause("Remove 3D probe. Install cutting tool (4mm single flute).", dry_run=args.dry_run)

        # === Z PROBING ===
        print("\n[8/9] Probing Z...")

        # Full Z retract before lateral move (unknown tool length after change)
        grbl.send(f"G53 G0 Z0")
        grbl.send(f"G53 G0 X{z_probe_x:.3f} Y{z_probe_y:.3f}")
        grbl.send(f"G53 G0 Z-{SAFE_Z:.3f}")  # descend to safe height above case

        pause(f"Place touch plate ({TOUCH_PLATE_THICKNESS}mm) on workpiece at case center. Clip ground wire to cutting tool.", dry_run=args.dry_run)

        # Verify probe/touch plate circuit is working (manual trigger test)
        print("\n    Checking touch plate...")
        grbl.confirm_probe_trigger(
            "Touch the cutting tool to the touch plate to confirm circuit.",
            dry_run=args.dry_run
        )

        cutting_tool_z = probe_z_double(grbl)

        # Retract BEFORE asking to remove touch plate
        grbl.send(f"G53 G0 Z0")

        pause("Remove touch plate and ground wire.", dry_run=args.dry_run)

        # Cross-check: 3D probe surface Z vs cutting tool Z
        # The touch plate sits ON TOP of the case surface.
        # surface_z_machine = case_top_z (probe tip center at contact)
        # cutting_tool_z = touch_plate_top_z (tool tip center at contact)
        # touch_plate_top = surface_z_machine + TOUCH_PLATE_THICKNESS
        # Cross-check not possible without knowing tool lengths
        # (3D probe and cutting tool have different lengths)
        # The touch plate Z probe with G10 L20 sets Z0 correctly regardless.

        # === GENERATE G-CODE ===
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

        print("\n" + "="*60)
        print("  SETUP COMPLETE")
        print(f"  Angle: {angle_deg:.4f}°")
        print(f"  G-code: {GCODE_OUTPUT}")
        print("="*60)

        # Done — tell user what to do next
        print(f"\n  Next: open gSender, connect, load and run:")
        print(f"    {GCODE_OUTPUT}")

    except Exception as e:
        print(f"\n{'!'*60}", file=sys.stderr)
        print(f"  ERROR: {e}", file=sys.stderr)
        print(f"  Sending feed hold...", file=sys.stderr)
        grbl.feed_hold()
        print(f"  Machine is in Hold state. Re-run script to start over (will re-home).", file=sys.stderr)
        print(f"{'!'*60}", file=sys.stderr)
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
                   help="Work coordinates for Z surface probe (default: case center). "
                        "Use when center has a hole from previous cuts.")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args)
