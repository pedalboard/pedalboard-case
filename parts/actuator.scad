include <BOSL2/std.scad>
include <BOSL2/threading.scad>

// based on https://www.cliffuk.co.uk/products/switches/FC7125.pdf

$fn=200;

module actuator() {
    screwlen = 14.3;
    up(screwlen/2) threaded_rod(d=12,l=screwlen,pitch=0.75);
    up(screwlen+2.05+5) cyl(l=5.1, d=10, chamfer=0.4);
    up(screwlen+2.6) cyl(l=5.2, d=8, chamfer=0.2);
    up(2.5) cyl(l=5, d=14, texture="ribs", tex_scale=0.1, tex_size=[0.3,0.3]);
    down(3) thread_helix(d2=3, d1=4.8, pitch=1, thread_depth=0.3, flank_angle=35, turns=6.5);
}

actuator();

