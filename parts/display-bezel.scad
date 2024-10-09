include <BOSL2/screws.scad>
include <BOSL2/std.scad>

$fn = 200;

$vpr = [ 31.27, 0.48, 199.20 ];
$vpt = [ -4.70, 2.48, -2.39 ];
$vpd = 185.25;

display_bezel();

module display_bezel()
{
    color([ 0.3, 0.3, 0.3, 1 ]) difference()
    {
        up(1) cuboid(size = [ 38, 52, 2 ], rounding = 1, except = BOTTOM);
        up(0.5) cuboid(size = [ 34, 37.5, 2 ]);
        up(0.5) cuboid(size = [ 15, 45.5, 2 ]);
        fwd(3) cuboid(size = [ 28, 28, 6 ]);
        fwd(21) right(13.5) up(2) screw_hole("M2", head = "flat", counterbore = 0, length = 10, anchor = TOP);
        fwd(21) left(13.5) up(2) screw_hole("M2", head = "flat", counterbore = 0, length = 10, anchor = TOP);
        back(21) right(13.5) up(2) screw_hole("M2", head = "flat", counterbore = 0, length = 10, anchor = TOP);
        back(21) left(13.5) up(2) screw_hole("M2", head = "flat", counterbore = 0, length = 10, anchor = TOP);
    }
}
