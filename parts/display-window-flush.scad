include <BOSL2/std.scad>

$fn = 100;

// Plexiglass display window (flush mount)
// Same step principle as LED ring — lip sits in case recess, step drops into cutout

// Case cutout (through-hole in case)
case_cutout_w = 34.5;       // mm — from top-panel-coords.json
case_cutout_h = 36.7;       // mm

// Plexiglass window dimensions
plexi_lip = 1.0;            // mm — lip overhang each side
plexi_top_w = case_cutout_w + 2*plexi_lip;   // 36.5mm
plexi_top_h = case_cutout_h + 2*plexi_lip;   // 38.7mm
plexi_step_w = case_cutout_w - 0.4;          // 34.1mm (clearance in hole)
plexi_step_h = case_cutout_h - 0.4;          // 36.3mm
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
