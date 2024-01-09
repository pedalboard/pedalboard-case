include <BOSL2/std.scad>
include <BOSL2/screws.scad>

display_bezel();

module display_bezel() {
    up(1) cuboid(size=[36,49,2], rounding=1, except=BOTTOM);
}


