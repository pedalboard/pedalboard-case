include <BOSL2/screws.scad>
include <BOSL2/std.scad>

$fn = 64;

$vpr = [ 31.27, 0.48, 199.20 ];
$vpt = [ -4.70, 2.48, -2.39 ];
$vpd = 185.25;

display_bezel();

module display_bezel()
{
    color([ 0.3, 0.3, 0.3, 1 ]) difference()
    {
        up(1) cuboid(size = [ 40, 58, 2 ], rounding = 0.5);
        cuboid(size = [ 30, 30, 6 ]);
        fwd(24) cuboid(size = [ 22, 12, 6 ]);
        fwd(20.75) right(15.14) trap();
        fwd(20.75) left(15.14) trap();
        back(20.75) right(15.14) trap();
        back(20.75) left(15.14) trap();
        back(26) left(15) trap();
        back(26) right(15) trap();
        fwd(26) left(15) trap();
        fwd(26) right(15) trap();
    }
}

module trap()
{
    nut_trap_inline(spec = "M1.6", length = 1);
    up(2) screw_hole("M1.6", length = 8);
}
