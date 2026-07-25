/*
 * fixture-plate.scad — CNC fixture plate for Hammond 1590DD top panel milling
 *
 * Screws down to SRcnc wasteboard via M5 carriage holes.
 * Case mounted open-side-down: screws go through plate up into case corner bosses.
 * Washer between screw head and MDF prevents pull-through.
 *
 * Coordinate system: center of plate = center of case = machine X110 Y190
 *
 * Wasteboard carriage hole pattern (from srcnc/scad/main.scad):
 *   X: ±ycarriage_separation/2 = ±60mm
 *   Y: ±yrail_separation/2     = ±90mm
 *   Screw: M5, head sits on top of plate
 *
 * 1590DD case screw hole pattern (from datasheet):
 *   X: ±89mm from case center
 *   Y: ±57mm from case center
 *   Screw: original case screws (#6-32 or M3), min ~10mm length
 *   Washer: ø10mm, sits in counterbore
 *
 * Material: 15mm MDF
 * Mill this plate on the SRcnc before using it as a fixture.
 */

// === PARAMETERS ===

plate_thickness = 15;       // mm — MDF thickness

// Wasteboard carriage holes — M5 through hole, screw head sits on top
carriage_hole_x = 60;       // ±mm from center
carriage_hole_y = 90;       // ±mm from center
carriage_screw_d = 5.4;     // M5 clearance

// Case screw holes — counterbored for washer+head, through hole for shank
// Original case screws (#6-32 or M3) + ø10mm washer
case_hole_x = 89;           // ±mm from center
case_hole_y = 57;           // ±mm from center
case_screw_d   = 4.0;       // shank clearance (peck drilled with 4mm tool)
case_cbore_d   = 11.0;      // counterbore for ø10mm washer + 0.5mm clearance
case_cbore_depth = 11.0;    // counterbore depth — leaves 4mm MDF below washer
                            // min screw length ~10mm (4mm plate + ~4-6mm into case boss)

// Plate size — large enough to cover all holes with margin
plate_w = 210;              // mm
plate_h = 200;              // mm

// === MODULES ===

module carriage_holes() {
    for (x = [-carriage_hole_x, carriage_hole_x])
        for (y = [-carriage_hole_y, carriage_hole_y])
            translate([x, y, 0]) children();
}

module case_holes() {
    // 4 corner screws
    for (x = [-case_hole_x, case_hole_x])
        for (y = [-case_hole_y, case_hole_y])
            translate([x, y, 0]) children();
    // 2 center screws on long sides (X=0, Y=±57)
    for (y = [-case_hole_y, case_hole_y])
        translate([0, y, 0]) children();
}

module fixture_plate() {
    difference() {
        // Plate body
        cube([plate_w, plate_h, plate_thickness], center=true);

        // Case screw holes — counterbore for washer+head, through hole for shank
        case_holes() {
            // Counterbore from top (washer + head recess)
            translate([0, 0, plate_thickness/2 - case_cbore_depth])
                cylinder(d=case_cbore_d, h=case_cbore_depth + 0.01, $fn=32);
            // Shank through hole
            translate([0, 0, -plate_thickness/2 - 0.01])
                cylinder(d=case_screw_d, h=plate_thickness + 0.02, $fn=32);
        }

        // Carriage holes — M5 through hole
        carriage_holes()
            translate([0, 0, -plate_thickness/2 - 0.01])
                cylinder(d=carriage_screw_d, h=plate_thickness + 0.02, $fn=32);
    }
}

// === RENDER ===

fixture_plate();
