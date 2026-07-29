include <BOSL2/std.scad>

$fn = 100;

// Plexiglass disc with step and center hole
plexi_od = 24.0;
plexi_step_od = 22.0;     // bottom step fits inside case hole
plexi_thickness = 2.0;
step_depth = 1.0;          // 1mm step at bottom
center_hole_d = 14.0;     // center hole for button actuator

color([0.3, 0.3, 0.3, 0.7])
difference() {
    cyl(d=plexi_od, h=plexi_thickness);
    // Step at bottom edge
    down(step_depth/2) tube(od=plexi_od+1, id=plexi_step_od, h=step_depth+0.1);
    // Center hole for button actuator
    cyl(d=center_hole_d, h=plexi_thickness+1);
}
