include <BOSL2/std.scad>
include <BOSL2/screws.scad>

// based on https://www.cliffuk.co.uk/products/switches/FC7125.pdf

$fn=200;

module actuator_nut() {
    nut(nut_info("M12x0.75",thickness=2), bevang=15, bevel=true, ibevel=true, blunt_start=false);
}

actuator_nut();

