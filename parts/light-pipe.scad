include <lib/actuator.scad>

$fn=200;

color(washer_color) union() {
    down(1) cyl(d=7, h=1, rounding1=1, center=false);
    cyl(d=6, h=18, center=false);
}
