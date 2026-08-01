include <BOSL2/std.scad>

$fn = 100;

// Plexiglass display window (flush mount)
// Same step principle as LED ring — lip sits in case recess, step drops into cutout

// Case cutout (through-hole in case) — asymmetric width (+5mm top, +3mm bottom)
case_cutout_w = 42.5;       // mm — enlarged for OLED clearance
case_cutout_h = 36.7;       // mm

// Case recess (1mm deep pocket)
case_recess_w = 44.5;       // mm
case_recess_h = 38.7;       // mm

// Plexiglass window dimensions — lip sits in recess
clearance = 0.3;         // mm — per side, for press-fit
plexi_top_w = case_recess_w - 2*clearance;    // fits in recess with clearance
plexi_top_h = case_recess_h - 2*clearance;
plexi_step_w = case_cutout_w - 2*clearance;   // fits in cutout with clearance
plexi_step_h = case_cutout_h - 2*clearance;
plexi_thickness = 2.0;      // mm total
step_depth = 1.0;           // mm — bottom step
corner_r = 2.0;             // mm — rounded corners (matches 4mm mill radius)

color([0.3, 0.3, 0.3, 0.7])
difference() {
    cuboid([plexi_top_w, plexi_top_h, plexi_thickness], rounding=corner_r, edges="Z");
    // Remove outer material from bottom half to create step
    down(step_depth/2) difference() {
        cuboid([plexi_top_w+1, plexi_top_h+1, step_depth+0.1]);
        cuboid([plexi_step_w, plexi_step_h, step_depth+0.2], rounding=corner_r, edges="Z");
    }
}
