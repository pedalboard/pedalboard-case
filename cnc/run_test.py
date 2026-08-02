#!/usr/bin/env python3
"""Run probe-setup.py against mock-machine.py and report results."""

import os
import subprocess
import sys
import time

# Start mock machine
mock = subprocess.Popen(
    ["python3", "mock-machine.py"],
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

# Run probe-setup against simulator
probe = subprocess.Popen(
    ["python3", "probe-setup.py", "--port", "/tmp/cnc-sim"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

# Send Enter for all interactive pauses
probe.stdin.write(b"\n" * 10)
probe.stdin.flush()

try:
    out, _ = probe.communicate(timeout=45)
except subprocess.TimeoutExpired:
    probe.kill()
    out, _ = probe.communicate()
    print("ERROR: probe-setup.py timed out", file=sys.stderr)
    sys.stdout.buffer.write(out)
    mock.terminate()
    sys.exit(1)
finally:
    mock.terminate()
    mock.wait()

sys.stdout.buffer.write(out)
sys.exit(probe.returncode)
