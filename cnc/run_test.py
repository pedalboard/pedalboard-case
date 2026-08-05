#!/usr/bin/env python3
"""Run probe-setup.py or engrave-setup.py against mock-machine.py and report results.

Usage:
    python3 run_test.py              # test probe-setup.py (nominal case)
    python3 run_test.py --engrave    # test engrave-setup.py (with 0.3mm crown)
    python3 run_test.py --angle 0.5  # add 0.5° rotation to mock machine
"""

import argparse
import os
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser(description="Run CNC setup scripts against mock machine")
    p.add_argument("--engrave", action="store_true",
                   help="Test engrave-setup.py instead of probe-setup.py")
    p.add_argument("--angle", type=float, default=0.0,
                   help="Simulated case rotation angle in degrees (default: 0.0)")
    p.add_argument("--crown", type=float, default=None,
                   help="Simulated surface crown in mm (default: 0.0 for probe, 0.3 for engrave)")
    args = p.parse_args()

    # Choose script under test
    if args.engrave:
        script   = "engrave-setup.py"
        crown    = args.crown if args.crown is not None else 0.3
    else:
        script   = "probe-setup.py"
        crown    = args.crown if args.crown is not None else 0.0

    # Start mock machine
    mock_cmd = ["python3", "mock-machine.py",
                "--angle", str(args.angle),
                "--crown", str(crown)]
    mock = subprocess.Popen(
        mock_cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for virtual port to appear
    deadline = time.time() + 10
    while not os.path.exists("/tmp/cnc-sim") and time.time() < deadline:
        time.sleep(0.2)

    if not os.path.exists("/tmp/cnc-sim"):
        mock.terminate()
        print("ERROR: Mock machine did not start (no /tmp/cnc-sim)", file=sys.stderr)
        sys.exit(1)

    print(f"Mock machine started  (angle={args.angle}°  crown={crown}mm)")
    print(f"Running: python3 {script} --port /tmp/cnc-sim")
    print()

    # Run setup script against simulator
    setup = subprocess.Popen(
        ["python3", script, "--port", "/tmp/cnc-sim"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Send Enter for all interactive pauses
    setup.stdin.write(b"\n" * 20)
    setup.stdin.flush()

    timeout = 120 if args.engrave else 45
    try:
        out, _ = setup.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        setup.kill()
        out, _ = setup.communicate()
        print(f"ERROR: {script} timed out", file=sys.stderr)
        sys.stdout.buffer.write(out)
        mock.terminate()
        sys.exit(1)
    finally:
        mock.terminate()
        mock.wait()

    sys.stdout.buffer.write(out)
    sys.exit(setup.returncode)


if __name__ == "__main__":
    main()
