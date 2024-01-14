include <../BOSL2/std.scad>
include <../BOSL2/screws.scad>

// based on https://www.cliffuk.co.uk/products/switches/FC7125.pdf

actuator_color = [219,226,233];

module actuator_nut() {
    spec = [["system","ISO"],
           ["type","nut_info"],
           ["shape", "hex"],
           ["pitch", 0.75],
           ["width",14],
           ["diameter",12],
           ["thickness",2]];
    color(actuator_color) nut(spec, bevang=15, bevel=true, ibevel=true, blunt_start=false);
}

module actuator() {
    screwlen = 14.3;
    color(actuator_color) union() {
        up(screwlen/2) threaded_rod(d=12,l=screwlen,pitch=0.75);
        up(screwlen+2.05+5) cyl(l=5.1, d=10, chamfer=0.4);
        up(screwlen+2.6) cyl(l=5.2, d=8, chamfer=0.2);
        up(2.5) cyl(l=5, d=14, texture="ribs", tex_scale=0.1, tex_size=[0.3,0.3]);
        down(3) thread_helix(d2=3, d1=4.8, pitch=1, thread_depth=0.3, flank_angle=35, turns=6.5);
    };
}

washer_color = [0.9,0.9,0.9,0.6];

module led_ring_washer() {
    color(washer_color) difference() {
        down(0.3) cyl(d=24, h=3, rounding2=1);
        cyl(d=13, h=5);
        down(2) tube(od=25, id=22.2, h=4);
        down(2) tube(od=20, id=16, h=4);
    }
}

module led_ring_rotary_washer() {
    color(washer_color) difference() {
        union() {
            down (0.3) cyl(d=24, h=3, rounding2=1);
            down(4) threaded_rod(d=12, l=5, pitch=0.75);
        }
        cyl(d=8, h=20);
        down(2) tube(od=25, id=22.2, h=4);
        down(2) tube(od=20, id=16, h=4);
    }
}


