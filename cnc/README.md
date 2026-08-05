# cnc/

Automated CNC setup scripts for the Hammond 1590DD top panel —
hole cutting and engraving on powder-coated aluminium.

## Files

| File | Purpose |
|------|---------|
| `grbl.py` | Shared GRBL/grblHAL serial protocol and probe helpers |
| `probe-setup.py` | Full setup for hole cutting: edges, angle, per-feature Z, G-code |
| `engrave-setup.py` | Setup for engraving: edges, angle, surface height map, engraving G-code |
| `mock-machine.py` | Machine simulator for testing without real hardware |
| `run_test.py` | Test runner (runs setup scripts against simulator) |

## Setup

```bash
pip install pyserial==3.5
```

## Workflow Overview

```
1. Mount case on fixture plate (open-side-down, centered at ~X=110 Y=190)
2. Close gSender

── HOLE CUTTING ──────────────────────────────────────────────────────────────
3. python3 cnc/probe-setup.py
   → installs 3D probe, finds centre+angle, per-feature Z offsets, touch plate Z
   → generates top-panel.nc
4. Open gSender, connect, load top-panel.nc, run

── ENGRAVING ─────────────────────────────────────────────────────────────────
5. python3 cnc/engrave-setup.py
   → installs 3D probe, finds centre+angle, probes 6×10 height map (38 points),
     skips holes, saves heightmap.json, generates engraving.nc via plates.py
   → installs V-bit, touch plate Z
6. Open gSender, connect, load engraving.nc, run
```

---

## probe-setup.py

Full automated setup for hole cutting.

**Usage:**
```bash
python3 probe-setup.py                     # full run
python3 probe-setup.py --dry-run           # print commands without connecting
python3 probe-setup.py --port /tmp/cnc-sim # test with simulator

# Rework (holes already cut — skip feature probing):
python3 probe-setup.py --skip-feature-probing --z-probe-offset 10 0
```

**Steps:**
1. Home machine (Z → X → Y)
2. Pause: install 3D probe
3. Probe spoilboard Z reference
4. Probe 5 case edges → centre + rotation angle, set G54 X0 Y0
5. Probe case surface Z at centre
6. Probe Z at 12 feature centres (buttons, encoders, displays, LEDs)
7. Pause: swap to cutting tool
8. Probe Z with touch plate → set G54 Z0
9. Generate `top-panel.nc` with angle + Z offsets

**Outputs:** `top-panel.nc`, `z-offsets.json`

---

## engrave-setup.py

Setup for engraving on the powder-coated panel surface.

The powder coat is non-conductive and ~0.1mm thick — the 3D mechanical
probe measures the actual coated surface. A 6×10 height map grid is probed
across the panel (~20mm spacing), skipping all hole positions. The height map
is applied to the engraving G-code via `plates.py --heightmap` so the V-bit
follows the actual surface rather than a flat plane.

**Usage:**
```bash
python3 engrave-setup.py                     # full run
python3 engrave-setup.py --dry-run           # print commands without connecting
python3 engrave-setup.py --port /tmp/cnc-sim # test with simulator

# If case centre has a hole (use an offset reference point):
python3 engrave-setup.py --z-probe-offset 10 0
```

**Steps:**
1. Home machine (Z → X → Y)
2. Pause: install 3D probe
3. Probe spoilboard Z reference
4. Probe 5 case edges → centre + rotation angle, set G54 X0 Y0
5. Probe reference surface Z at centre
6. Probe 6×10 grid (38 points after skipping holes) → `heightmap.json`
7. Generate `engraving.nc` via `plates.py --heightmap`
8. Pause: swap to V-bit
9. Probe Z with touch plate → set G54 Z0

**Outputs:** `engraving.nc`, `heightmap.json`

### Height Map Grid

```
Grid: 6 cols × 10 rows  (~20mm spacing)
Bounds: ±53.9mm X, ±87.9mm Y (3mm margin from each edge)
Hole avoidance: buttons/encoders r=14.2mm, LEDs r=6mm,
                bezel holes r=5mm, displays 25×21mm rect
Skipped points filled by nearest-neighbour for complete JSON grid.
```

---

## mock-machine.py

GRBL/grblHAL machine simulator for testing without real hardware.

```bash
python3 mock-machine.py                       # nominal case
python3 mock-machine.py --angle 0.5           # 0.5° rotation
python3 mock-machine.py --offset-x 2.0        # case shifted 2mm in X
python3 mock-machine.py --crown 0.3           # 0.3mm sinusoidal surface crown
python3 mock-machine.py --angle 0.3 --crown 0.4  # combined
```

The `--crown` option simulates a typical die-cast aluminium panel: the surface
is highest at the centre and tapers to zero at the edges following a
cosine profile. Typical powder-coated cases: 0.3–0.5mm.

---

## Testing

```bash
make test           # run probe-setup.py against simulator
make test-engrave   # run engrave-setup.py against simulator (with 0.3mm crown)

# Manual testing with custom parameters:
python3 run_test.py --angle 0.5
python3 run_test.py --engrave --crown 0.5
```

### Testing with two terminals

```bash
# Terminal 1 — start simulator
python3 mock-machine.py --angle 0.3 --crown 0.3

# Terminal 2 — run setup
python3 probe-setup.py --port /tmp/cnc-sim
# or
python3 engrave-setup.py --port /tmp/cnc-sim
```

---

## XY Probing Geometry

Same for both scripts — 5 edge probes, no case dimension assumptions:

```
              You stand here (Y=0)

    Y
    ↑
    │
    ┊                  ┌───────────────────────┐
250 ┊ ─ ─ ─ ②·→→→→→→→→→█           ·⑤          │
    │                  │       X=110,Y=291     │
190 ┊                  │       CENTER          █←·③
    │                  │     (110, 190)        │ X=177
130 ┊ ─ ─ ─ ①·→→→→→→→→→█                       │
    ┊                  └───────────────────────┘
 89 ┊                          ·④
    └──────────────────────────── → X
   0      43  53              167 177  220

  ① X- front  Y=130  → +X   left edge + angle pt 1
  ② X- back   Y=250  → +X   left edge + angle pt 2
  ③ X+ edge   Y=190  ← -X   right edge
  ④ Y- edge   X=110  ↑ +Y   front edge
  ⑤ Y+ edge   X=110  ↓ -Y   back edge

  X centre = (avg(①,②) + ③) / 2
  Y centre = (④ + ⑤) / 2
  Angle    = atan2(②x − ①x, 120mm)
```
