include <BOSL2/std.scad>
include <BOSL2/threading.scad>

// based on https://www.cliffuk.co.uk/products/switches/FC7125.pdf

$fn=200;

module led_ring_washer() {
    difference() {
        cyl(d=24, h=3, rounding1=1);
        cyl(d=13, h=4);
        up(1) tube(od=25, id=22.2, h=2);
        up(1.5) tube(od=19, id=17, h=1);
    }
}

led_ring_washer();

