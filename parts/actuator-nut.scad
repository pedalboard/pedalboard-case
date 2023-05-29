include <BOSL2/std.scad>
include <BOSL2/screws.scad>

// based on https://www.cliffuk.co.uk/products/switches/FC7125.pdf

$fn=200;

module actuator_nut() {
    spec = [["system","ISO"],
           ["type","nut_info"],
           ["shape", "hex"],
           ["pitch", 0.75],
           ["width",14],
           ["diameter",12],
           ["thickness",2]];
    nut(spec, bevang=15, bevel=true, ibevel=true, blunt_start=false);
}

actuator_nut();

