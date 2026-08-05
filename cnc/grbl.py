"""
grbl.py — Shared GRBL/grblHAL serial protocol and probe helpers.

Used by probe-setup.py and engrave-setup.py.
"""

import re
import sys
import time

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: make install", file=sys.stderr)
    sys.exit(1)

# === TIMING ===

TIMEOUT         = 90.0    # seconds — wait for probe response
HOMING_TIMEOUT  = 120.0   # seconds — wait for homing cycle

# === PROBE FEEDS ===

FEED_FAST  = 100.0   # mm/min — fast probe approach
FEED_SLOW  =  20.0   # mm/min — slow probe (accurate)

# === GRBL CONNECTION ===

class GrblConnection:
    """Minimal GRBL/grblHAL serial protocol handler."""

    def __init__(self, port, baud, dry_run=False):
        self.dry_run = dry_run
        self.conn = None
        if not dry_run:
            self.conn = serial.Serial(port, baud, timeout=1)
            time.sleep(2)
            self.conn.flushInput()
            self._read_startup()

    def _read_startup(self):
        deadline = time.time() + 5.0
        while time.time() < deadline:
            line = self.conn.readline().decode("ascii", errors="replace").strip()
            if line:
                print(f"  < {line}")
                deadline = time.time() + 1.0

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
        """Send a probe command, return (x, y, z) of contact point."""
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
                    return prb
            if line.startswith("ok"):
                ok_received = True
                if prb is not None:
                    return prb
            if line.startswith("error"):
                raise RuntimeError(f"GRBL error during probe: {line}")
        if ok_received and prb is None:
            raise RuntimeError("Got 'ok' but no [PRB:] response — probe input may not be connected")
        raise TimeoutError("Timeout waiting for probe response")

    def feed_hold(self):
        """Send feed hold (!) immediately."""
        print("  > ! (FEED HOLD)")
        if self.dry_run:
            return
        self.conn.write(b"!")

    def check_probe_ready(self):
        """Verify probe input is NOT triggered."""
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
        """Wait for probe to be touched and released (interactive confirmation)."""
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

        while True:
            self.conn.write(b"?\n")
            time.sleep(0.3)
            while self.conn.in_waiting:
                line = self.conn.readline().decode("ascii", errors="replace").strip()
                if line.startswith("<") and "Pn:" in line:
                    pn = line.split("Pn:")[1].split("|")[0]
                    if "P" in pn:
                        print("    Probe triggered \u2713")
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
        """Query $# and return G54 (x, y, z) offsets."""
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
        """Query machine state. Handle Hold/Alarm."""
        if self.dry_run:
            return
        self.conn.write(b"?\n")
        deadline = time.time() + 5.0
        while time.time() < deadline:
            line = self.conn.readline().decode("ascii", errors="replace").strip()
            if line.startswith("<"):
                if "Hold" in line:
                    print("  Machine in Hold state — sending soft reset...")
                    self.conn.write(b"\x18")
                    time.sleep(2)
                    while self.conn.in_waiting:
                        self.conn.readline()
                    return
                if "Alarm" in line:
                    print("  Machine in Alarm state — will unlock and re-home...")
                    return
                return
        raise TimeoutError("Timeout waiting for machine state response")

    def close(self):
        if self.conn:
            self.conn.close()


# === PROBE HELPERS ===

def probe_edge_double(grbl, axis, direction, label):
    """Probe an edge with fast then slow approach.

    Returns contact position along axis (machine coordinate).
    """
    travel = 35.0 * direction
    retract = 2.0 * -direction

    print(f"\n--- Probing {label} ---")

    grbl.send("G91")
    fast_result = grbl.probe(f"G38.2 {axis}{travel:.3f} F{FEED_FAST}")
    grbl.send(f"G0 {axis}{retract:.3f}")
    slow_travel = (35.0 / 5.0) * direction
    slow_result = grbl.probe(f"G38.2 {axis}{slow_travel:.3f} F{FEED_SLOW}")
    grbl.send(f"G0 {axis}{retract:.3f}")
    grbl.send("G90")

    idx = {"X": 0, "Y": 1, "Z": 2}[axis]
    fast_contact = fast_result[idx]
    slow_contact = slow_result[idx]

    agreement = abs(fast_contact - slow_contact)
    if agreement > 0.5:
        raise RuntimeError(
            f"Probe fast/slow disagreement on {label}: "
            f"fast={fast_contact:.4f}, slow={slow_contact:.4f}, diff={agreement:.4f}mm"
        )
    print(f"    {label} contact: {axis}={slow_contact:.4f} (agreement: {agreement:.4f}mm)")
    return slow_contact


def probe_z_double(grbl, travel=80.0):
    """Probe Z with fast then slow approach. Returns machine Z contact."""
    print("\n--- Probing Z ---")
    grbl.send("G91")
    fast_result = grbl.probe(f"G38.2 Z-{travel:.3f} F{FEED_FAST}")
    grbl.send("G0 Z2.0")
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
    print(f"    Z contact: {slow_z:.4f} (agreement: {agreement:.4f}mm)")
    return slow_z


def probe_z_surface(grbl, travel=80.0):
    """Probe surface Z with double contact. Returns machine Z contact."""
    print("\n--- Probing surface Z ---")
    grbl.send("G91")
    fast_result = grbl.probe(f"G38.2 Z-{travel:.3f} F{FEED_FAST}")
    grbl.send("G0 Z2.0")
    slow_result = grbl.probe(f"G38.2 Z-5.000 F{FEED_SLOW}")
    grbl.send("G90")

    fast_z = fast_result[2]
    slow_z = slow_result[2]
    agreement = abs(fast_z - slow_z)
    if agreement > 0.5:
        raise RuntimeError(
            f"Surface Z probe fast/slow disagreement: "
            f"fast={fast_z:.4f}, slow={slow_z:.4f}, diff={agreement:.4f}mm"
        )
    surface_z = slow_z
    print(f"    Surface Z: {surface_z:.4f} (agreement: {agreement:.4f}mm)")
    return surface_z


def probe_spoilboard(grbl, x, y, safe_z, travel=80.0):
    """Probe spoilboard at a reference position. Returns machine Z contact."""
    print(f"\n--- Probing spoilboard at X={x:.1f} Y={y:.1f} ---")
    grbl.send(f"G53 G0 X{x:.3f} Y{y:.3f}")
    grbl.send(f"G53 G0 Z-{safe_z:.3f}")
    grbl.send("G91")
    fast_result = grbl.probe(f"G38.2 Z-{travel:.3f} F{FEED_FAST}")
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
    print(f"    Spoilboard Z: {slow_z:.4f} (agreement: {agreement:.4f}mm)")
    return slow_z


def check_plausibility(label, value, expected, tolerance):
    """Raise if value is outside expected ± tolerance."""
    error = abs(value - expected)
    if error > tolerance:
        raise RuntimeError(
            f"Plausibility check failed: {label}\n"
            f"  Expected: {expected:.3f} ± {tolerance:.1f}\n"
            f"  Got:      {value:.3f}  (error: {error:.3f})"
        )


def pause(msg, dry_run=False):
    """Print message and wait for user confirmation."""
    print(f"\n{'='*60}")
    print(f"  ACTION REQUIRED: {msg}")
    print(f"{'='*60}")
    if dry_run:
        print("  [dry-run: skipping]")
        return
    input("  Press Enter to continue...")
