include <BOSL2/std.scad>

$fn = 100;

// Simple plexiglass disc for single LED light pipe
// Press-fits into ø6mm recess (0.5mm deep) + ø5mm through-hole in case
lightpipe_d = 6.0;          // mm
lightpipe_h = 2.0;          // mm

color([0.3, 0.3, 0.3, 0.7])
cyl(d=lightpipe_d, h=lightpipe_h);
