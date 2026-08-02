# cnc/

Automated CNC setup scripts for milling the Hammond 1590DD top panel.

## Scripts

### probe-setup.py

Full automated setup: homing, edge finding, center/angle computation,
per-feature Z probing, Z probing with touch plate, and G-code generation.

**Preconditions:**
- Case mounted open-side-down on fixture plate, centered at ~X=110 Y=190
- gSender closed (script owns `/dev/cnc`)
- Machine in idle state

**Usage:**
```bash
python3 probe-setup.py                     # full run
python3 probe-setup.py --dry-run           # print all commands without connecting
python3 probe-setup.py --port /tmp/cnc-sim # connect to simulator

# Rework (case already has holes):
python3 probe-setup.py --skip-feature-probing --z-probe-offset 10 0
```

### XY Probing Geometry

5 edge probes to find center and angle without assuming case dimensions:

```
              You stand here (Y=0)

    Y
    ↑
    │
    ┊                  ┌───────────────────────┐
    │                  │                       │
    │                  │          ·⑤           │
    │                  │      X=110,Y=291      │
    │                  │          ↓            │
250 ┊─ ─ ─ ②·→→→→→→→→→█                       │
    │       X=43       │                       │
    │                  │                       │
    │                  │       CENTER          │
190 ┊                  │     (110, 190)        █←←←←←←←·③
    │                  │                       │    X=177
    │                  │                       │
130 ┊─ ─ ─ ①·→→→→→→→→→█                       │
    │       X=43       │                       │
    │                  │                       │
    ┊                  └───────────────────────┘
    │                          ↑
    │                          ↑
 89 ┊                          ·④
    │                      X=110
    └──────────────────────────────────────────── → X
   0          43    53                  167  177   220


    Probe       Start position    Direction   Purpose
    ─────────────────────────────────────────────────────
    ① X- front   X=43,  Y=130     → +X       left edge + angle pt 1
    ② X- back    X=43,  Y=250     → +X       left edge + angle pt 2
    ③ X+ edge    X=177, Y=190     ← -X       right edge
    ④ Y- edge    X=110, Y=89      ↑ +Y       front edge
    ⑤ Y+ edge    X=110, Y=291     ↓ -Y       back edge

    Calculations (no case dimension assumptions):
      X center = (avg(①,②) + ③) / 2
      Y center = (④ + ⑤) / 2
      Angle    = atan2(②_x - ①_x, 120mm)
```

All probes descend to 5mm below the case top surface before probing
sideways. Each probe uses double-contact (fast at 100mm/min, slow at
20mm/min) for accuracy. Tip radius cancels when taking midpoints of
opposing edges.

### Z Probing

After XY is established:
1. 3D probe measures case top surface at center (reference)
2. 3D probe measures Z at each of 12 feature centers (surface compensation)
3. Cutting tool + touch plate (19.25mm) measures Z for G54 Z0

**Safety features:**
- Feed hold on any error
- Probe trigger confirmation (touch-and-release) before probing
- All lateral moves preceded by full Z retract
- Double-contact probing (fast + slow) on all axes
- Fast/slow agreement check (≤0.5mm)
- Plausibility checks: case width, center position, rotation angle

### mock-machine.py

GRBL/grblHAL machine simulator for testing without real hardware.
Creates a virtual serial port with realistic probe contact geometry.

```bash
python3 mock-machine.py                    # nominal case
python3 mock-machine.py --angle 0.5        # 0.5° rotation
python3 mock-machine.py --offset-x 2.0     # shifted 2mm
```

## Setup

```bash
pip install pyserial==3.5
```

## Testing

```bash
make test   # run probe-setup against mock machine
```

## Workflow

```
1. Mount case on fixture plate
2. Close gSender
3. python3 cnc/probe-setup.py
4. Open gSender, connect, load top-panel.nc
5. Makita dial 1, WD-40, start job, override feed to 150%
```
