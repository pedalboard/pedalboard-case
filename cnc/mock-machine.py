#!/usr/bin/env python3
"""
mock-machine.py — GRBL/FluidNC machine simulator for testing probe-setup.py.

Creates a virtual serial port pair using Python pty. Simulates a machine
with a Hammond 1590DD case mounted at a configurable position and angle.

Usage:
    python3 mock-machine.py                    # default: case at X=110 Y=190, angle=0°
    python3 mock-machine.py --angle 0.5        # simulate 0.5° rotation
    python3 mock-machine.py --offset-x 2.0    # case shifted 2mm in X
    python3 mock-machine.py --case-height 2.5  # case wall thickness

Then in another terminal:
    python3 probe-setup.py --port /tmp/cnc-sim

The mock prints all commands received and responses sent.
"""

import argparse
import math
import os
import pty
import re
import sys
import threading
import time

# === SIMULATED MACHINE GEOMETRY ===

# Machine travel limits (machine coordinates, negative = below home)
MACHINE_X_MAX = 220.0
MACHINE_Y_MAX = 380.0
MACHINE_Z_MAX = 95.0   # distance from Z home to Z limit

# Default case position (center, machine coords)
DEFAULT_CASE_CENTER_X = 110.0
DEFAULT_CASE_CENTER_Y = 190.0
DEFAULT_CASE_HALF_WIDTH = 113.8 / 2.0   # short axis (X)
DEFAULT_CASE_HALF_HEIGHT = 181.8 / 2.0  # long axis (Y)

# Spoilboard (fixture plate) is elevated — not at machine Z limit
# Measured: fixture plate top surface at 65mm below home
SPOILBOARD_Z_MACHINE = -65.0

# Probe tip radius (must match probe-setup.py)
PROBE_TIP_RADIUS = 2.0

# Virtual serial port symlink
SYMLINK = "/tmp/cnc-sim"


class MockMachine:
    """Simulates a GRBL/FluidNC controller with a mounted case."""

    def __init__(self, args):
        self.args = args

        # Simulated case geometry (with offset and angle)
        self.case_center_x = DEFAULT_CASE_CENTER_X + args.offset_x
        self.case_center_y = DEFAULT_CASE_CENTER_Y + args.offset_y
        self.angle_rad = math.radians(args.angle)

        # Case surface Z in machine coords
        # Spoilboard is at -MACHINE_Z_MAX, case sits on spoilboard
        self.case_surface_z = SPOILBOARD_Z_MACHINE + args.case_height

        # Touch plate: placed on top of case surface during Z probing
        # Simulated as always present for Z probes when over the case
        self.touch_plate_thickness = args.touch_plate

        # Simulated machine position (machine coords)
        self.pos = [0.0, 0.0, 0.0]  # X, Y, Z (Z=0 = home = top)
        self.homed = False
        self.state = "Idle"
        self.incremental = False  # G91 mode
        self.touch_plate_active = False  # set to True when touch plate is placed
        self.z_probe_count = 0  # track Z probe sequences (2nd = cutting tool + plate)

        # WCS G54 offsets
        self.g54 = [0.0, 0.0, 0.0]

    def _rotated_edge(self, nominal_x, nominal_y, probe_axis, direction):
        """Compute where a probe along probe_axis/direction contacts the case edge.

        Applies the simulated angle rotation to the case edges.
        Returns contact position in machine coords.
        """
        # Transform probe position into case-local coords
        # (reverse rotation by -angle)
        cx = self.case_center_x
        cy = self.case_center_y
        cos_a = math.cos(-self.angle_rad)
        sin_a = math.sin(-self.angle_rad)

        if probe_axis == "X":
            # Probing along X, Y is fixed
            # Case edge in local coords: x = ±half_width
            edge_local_x = DEFAULT_CASE_HALF_WIDTH * (-direction)
            # Transform edge point back to machine coords
            edge_machine_x = cx + edge_local_x * math.cos(self.angle_rad)
            edge_machine_y = cy + edge_local_x * math.sin(self.angle_rad)
            # Contact X = edge + probe tip offset
            contact_x = edge_machine_x + PROBE_TIP_RADIUS * direction
            return contact_x

        elif probe_axis == "Y":
            # Probing along Y at a given X position
            # Find Y of case edge at probe X in machine coords
            # Probe X in case-local coords
            probe_x_local = (nominal_x - cx) * cos_a - (self.pos[1] - cy) * sin_a
            # Edge Y in local coords: y = -half_height (Y- edge)
            edge_local_y = -DEFAULT_CASE_HALF_HEIGHT
            # Transform edge point back to machine coords at probe_x_local
            edge_machine_y = cy + probe_x_local * sin_a + edge_local_y * math.cos(self.angle_rad)
            # Contact Y = edge + probe tip offset
            contact_y = edge_machine_y + PROBE_TIP_RADIUS * direction
            return contact_y

        elif probe_axis == "Z":
            # Z probe — contact at case surface or spoilboard
            return None  # handled separately

    def _handle_probe(self, cmd):
        """Parse G38.x command and compute contact point.

        Returns (triggered, x, y, z) tuple.
        """
        # Parse: G38.2 X20 F100 or G38.3 Z-25 F100 etc.
        m = re.match(r"G38\.[2345]\s+([XYZ])([+-]?\d+\.?\d*)\s+F[\d.]+", cmd, re.I)
        if not m:
            return (False, *self.pos)

        axis = m.group(1).upper()
        travel = float(m.group(2))
        idx = ["X", "Y", "Z"].index(axis)

        # Target in machine coords (incremental or absolute)
        if self.incremental:
            target = self.pos[idx] + travel
        else:
            target = travel

        direction = 1 if target > self.pos[idx] else -1
        triggered = False
        contact = list(self.pos)

        if axis == "X":
            # X edge contact — apply rotation for angle
            cos_a = math.cos(-self.angle_rad)
            sin_a = math.sin(-self.angle_rad)
            # Probe Y in case-local coords
            probe_y_local = ((self.pos[0] - self.case_center_x) * sin_a
                             + (self.pos[1] - self.case_center_y) * cos_a)
            edge_local_x = -DEFAULT_CASE_HALF_WIDTH * direction
            edge_machine_x = (self.case_center_x
                              + edge_local_x * math.cos(self.angle_rad)
                              - probe_y_local * math.sin(self.angle_rad))
            contact_x = edge_machine_x + PROBE_TIP_RADIUS * direction
            if direction > 0 and self.pos[0] < contact_x <= target:
                contact[0] = contact_x
                triggered = True
            elif direction < 0 and target <= contact_x < self.pos[0]:
                contact[0] = contact_x
                triggered = True

        elif axis == "Y":
            # Y edge contact — apply rotation for angle
            cos_a = math.cos(-self.angle_rad)
            sin_a = math.sin(-self.angle_rad)
            # Probe X in case-local coords
            probe_x_local = ((self.pos[0] - self.case_center_x) * cos_a
                             - (self.pos[1] - self.case_center_y) * sin_a)
            edge_local_y = -DEFAULT_CASE_HALF_HEIGHT * direction
            edge_machine_y = (self.case_center_y
                              + probe_x_local * sin_a
                              + edge_local_y * math.cos(self.angle_rad))
            contact_y = edge_machine_y + PROBE_TIP_RADIUS * direction
            if direction > 0 and self.pos[1] < contact_y <= target:
                contact[1] = contact_y
                triggered = True
            elif direction < 0 and target <= contact_y < self.pos[1]:
                contact[1] = contact_y
                triggered = True

        elif axis == "Z":
            if direction < 0:
                # Determine which surfaces are present at current XY position
                surfaces = [SPOILBOARD_Z_MACHINE]  # spoilboard is always present

                # Check if XY is within case footprint
                dx = self.pos[0] - self.case_center_x
                dy = self.pos[1] - self.case_center_y
                cos_a = math.cos(-self.angle_rad)
                sin_a = math.sin(-self.angle_rad)
                local_x = dx * cos_a - dy * sin_a
                local_y = dx * sin_a + dy * cos_a
                over_case = (abs(local_x) < DEFAULT_CASE_HALF_WIDTH and
                             abs(local_y) < DEFAULT_CASE_HALF_HEIGHT)

                if over_case:
                    surfaces.append(self.case_surface_z)
                    # Touch plate sits on top of case surface when active
                    if self.touch_plate_active:
                        surfaces.append(self.case_surface_z + self.touch_plate_thickness)

                # Check surfaces from top to bottom
                for surface_z in sorted(surfaces, reverse=True):
                    contact_z = surface_z + PROBE_TIP_RADIUS
                    if self.pos[2] > contact_z >= target:
                        contact[2] = contact_z
                        triggered = True
                        break
                    elif self.pos[2] > surface_z >= target:
                        contact[2] = surface_z
                        triggered = True
                        break

        if triggered:
            self.pos = list(contact)
        else:
            self.pos[idx] = target

        return (triggered, *contact)

    def process(self, line):
        """Process a command line, return list of response lines."""
        line = line.strip()
        if not line:
            return []

        print(f"  RX: {line}")
        responses = []

        # Real-time commands
        if line == "?":
            mpos = f"{self.pos[0]:.3f},{self.pos[1]:.3f},{self.pos[2]:.3f}"
            responses.append(f"<{self.state}|MPos:{mpos}|FS:0,0>")
            return responses  # no 'ok' for ?

        # $# coordinate offsets
        if line == "$#":
            g54_str = f"{self.g54[0]:.3f},{self.g54[1]:.3f},{self.g54[2]:.3f}"
            responses.append(f"[G54:{g54_str}]")
            responses.append("ok")
            return responses

        # Homing
        if line in ("$H", "$HX", "$HY", "$HZ"):
            if line == "$HZ" or line == "$H":
                self.pos[2] = 0.0
            if line == "$HX" or line == "$H":
                self.pos[0] = 0.0
            if line == "$HY" or line == "$H":
                self.pos[1] = 0.0
            self.homed = True
            responses.append("ok")
            return responses

        # Alarm clear
        if line == "$X":
            self.state = "Idle"
            responses.append("ok")
            return responses

        # G10 L20 — set WCS offset
        m = re.match(r"G10\s+L20\s+P1\s+(.*)", line, re.I)
        if m:
            coords = m.group(1)
            for axis_m in re.finditer(r"([XYZ])([+-]?\d+\.?\d*)", coords, re.I):
                axis = axis_m.group(1).upper()
                val = float(axis_m.group(2))
                idx = ["X", "Y", "Z"].index(axis)
                # G10 L20 sets WCS so current pos = val
                # offset = machine_pos - val
                self.g54[idx] = self.pos[idx] - val
            responses.append("ok")
            return responses

        # G53 G38.x — probe in machine coordinates (safe descent)
        m = re.match(r"G53\s+(G38\.[2345]\s+.*)", line, re.I)
        if m:
            probe_cmd = m.group(1)
            old_incremental = self.incremental
            self.incremental = False
            triggered, cx, cy, cz = self._handle_probe(probe_cmd)
            self.incremental = old_incremental
            # G38.3/G38.5 (no-error variants) — only send ok, no PRB response
            # to avoid confusing subsequent probe() calls
            if re.match(r"G38\.[35]", probe_cmd, re.I):
                responses.append("ok")
            else:
                flag = "1" if triggered else "0"
                prb = f"{cx:.3f},{cy:.3f},{cz:.3f}"
                responses.append(f"[PRB:{prb}:{flag}]")
                if not triggered:
                    responses.append("error:5")
                else:
                    responses.append("ok")
            return responses

        # G38.x probe commands
        if re.match(r"G38\.[2345]", line, re.I):
            # Track Z probes to auto-activate touch plate on 2nd Z probe sequence
            if re.search(r"Z[+-]?\d", line, re.I):
                self.z_probe_count += 1
                if self.z_probe_count >= 4:  # spoilboard(2) + case surface(2) done; cutting tool probes
                    self.touch_plate_active = True
            triggered, cx, cy, cz = self._handle_probe(line)
            flag = "1" if triggered else "0"
            prb = f"{cx:.3f},{cy:.3f},{cz:.3f}"
            responses.append(f"[PRB:{prb}:{flag}]")
            if not triggered and "G38.2" in line.upper():
                responses.append("error:5")  # probe not triggered
            else:
                responses.append("ok")
            return responses

        # G53 modal + move — update position
        m = re.match(r"G53\s+G[01]\s+(.*)", line, re.I)
        if m:
            coords = m.group(1)
            for axis_m in re.finditer(r"([XYZ])([+-]?\d+\.?\d*)", coords, re.I):
                axis = axis_m.group(1).upper()
                val = float(axis_m.group(2))
                self.pos[["X","Y","Z"].index(axis)] = val
            responses.append("ok")
            return responses

        # G0/G1 moves (WCS or incremental)
        if re.match(r"G[01]\b", line, re.I):
            for axis_m in re.finditer(r"([XYZ])([+-]?\d+\.?\d*)", line, re.I):
                axis = axis_m.group(1).upper()
                val = float(axis_m.group(2))
                idx = ["X", "Y", "Z"].index(axis)
                if self.incremental:
                    self.pos[idx] += val
                else:
                    # WCS: machine pos = g54_offset + wcs_val
                    self.pos[idx] = self.g54[idx] + val
            responses.append("ok")
            return responses

        # G90/G91/G17/G21 modal — just ack
        if re.match(r"G(90|91|17|21)\b", line, re.I):
            if "G91" in line.upper():
                self.incremental = True
            elif "G90" in line.upper():
                self.incremental = False
            responses.append("ok")
            return responses

        # M3/M5 spindle
        if re.match(r"M[35]\b", line, re.I):
            responses.append("ok")
            return responses

        # Unknown — ack anyway
        responses.append("ok")
        return responses


def serve(machine, slave_fd, recorder=None, recorder_path=None):
    """Read commands from slave_fd, write responses."""
    buf = b""
    while True:
        try:
            data = os.read(slave_fd, 256)
        except OSError:
            break
        buf += data
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            cmd = line.decode("ascii", errors="replace").strip()
            if not cmd:
                continue
            # Record all non-realtime G-code commands (skip ok/error responses
            # and non-motion commands that don't visualize well)
            skip_prefixes = ("ok", "error", "<", "[", "Grbl", "$", "G10", "M")
            if (recorder is not None and cmd != "?"
                    and not cmd.startswith(skip_prefixes)):
                recorder.append(cmd)
                # Write incrementally so file is saved even on abrupt exit
                with open(recorder_path, "a") as f:
                    sanitized = re.sub(r"G38\.[2345]", "G0", cmd, flags=re.I)
                    sanitized = re.sub(r"\s*F[\d.]+", "", sanitized)
                    f.write(sanitized + "\n")
            responses = machine.process(cmd)
            for r in responses:
                print(f"  TX: {r}")
                os.write(slave_fd, (r + "\r\n").encode("ascii"))
                time.sleep(0.01)  # small delay to simulate real hardware


def main():
    p = argparse.ArgumentParser(description="GRBL/FluidNC machine simulator")
    p.add_argument("--angle", type=float, default=0.0,
                   help="Simulated case rotation angle in degrees (default: 0.0)")
    p.add_argument("--offset-x", type=float, default=0.0,
                   help="Case center X offset from nominal in mm (default: 0.0)")
    p.add_argument("--offset-y", type=float, default=0.0,
                   help="Case center Y offset from nominal in mm (default: 0.0)")
    p.add_argument("--case-height", type=float, default=30.0,
                   help="Case wall height in mm (default: 30.0)")
    p.add_argument("--touch-plate", type=float, default=19.25,
                   help="Touch plate thickness in mm (default: 19.25)")
    p.add_argument("--symlink", default=SYMLINK,
                   help=f"Virtual port symlink path (default: {SYMLINK})")
    p.add_argument("--save-gcode", type=str, default=None,
                   help="Save all received G-code commands to this file for visualization (e.g. setup-path.nc)")
    args = p.parse_args()

    machine = MockMachine(args)

    # Create virtual serial port pair
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)

    # Create symlink for easy access
    if os.path.exists(args.symlink) or os.path.islink(args.symlink):
        os.remove(args.symlink)
    os.symlink(slave_name, args.symlink)

    recorder = [] if args.save_gcode else None

    print(f"Mock machine started")
    print(f"  Virtual port: {slave_name}")
    print(f"  Symlink:      {args.symlink}")
    print(f"  Case center:  X={machine.case_center_x:.1f} Y={machine.case_center_y:.1f}")
    print(f"  Angle:        {args.angle:.3f}°")
    print(f"  Case height:  {args.case_height}mm")
    if args.save_gcode:
        print(f"  Recording to: {args.save_gcode}")
        with open(args.save_gcode, "w") as f:
            f.write("; Setup path recorded by mock-machine.py\n")
            f.write(f"; Angle: {args.angle}°  Offset: X={args.offset_x} Y={args.offset_y}\n")
            f.write("G21\nG90\n\n")
    print(f"\nConnect with:")
    print(f"  python3 probe-setup.py --port {args.symlink}")
    print(f"\nPress Ctrl+C to stop.\n")

    try:
        # Send startup greeting like GRBL
        time.sleep(0.1)
        os.write(master_fd, b"Grbl 1.1h ['$' for help]\r\n")

        serve(machine, master_fd, recorder=recorder, recorder_path=args.save_gcode)
    except KeyboardInterrupt:
        pass
    finally:
        os.close(master_fd)
        os.close(slave_fd)
        if os.path.exists(args.symlink):
            os.remove(args.symlink)
        if args.save_gcode and recorder:
            print(f"\nSaved {len(recorder)} commands to: {args.save_gcode}")
        print("\nMock machine stopped.")


if __name__ == "__main__":
    main()
