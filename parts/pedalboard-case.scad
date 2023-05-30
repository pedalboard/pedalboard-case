// pedalboard case

$fn=200;

length = 180;
width= 120;
height = 33;
cornerRadius = 1;
thickness = 2;
lugRadius = 3.5;
lidTolerance = 0.3;
pcbBottom = 13;

pcbHeight = thickness+15.8; // given by the button

// box
difference() {
    lugHeight = 6;
    nutTrapHeight = 2.5; // M3 mmax=2.4
    union() {
        difference() {
            roundedBox(width, length, height, cornerRadius);
            translate([thickness,thickness,thickness]) {
                roundedBox(width-(2*thickness), length-(2*thickness), height, cornerRadius);
            }
        }
        translate([0,0, height-lugHeight]) {
            place_lugs(width, length, lugRadius) cylinder(r=lugRadius, h=lugHeight);
        }
        translate([0,0, height-lugHeight-2*nutTrapHeight]) {
            place_lugs(width, length, lugRadius) cylinder(r=lugRadius, h=nutTrapHeight);
        }

    }
    translate([0,0,height-lugHeight+2*thickness]){
        tappingDrill = 2.5; // M3 tapping drill size
        place_lugs(width, length, lugRadius) cylinder(d=tappingDrill, h=lugHeight);
    }

    translate([0,0,height-lugHeight-nutTrapHeight]){
        place_lugs(width, length, lugRadius) nut_trap(w=5.5, h=nutTrapHeight);
    }

    button(0,6);
    button(0,58);
    button(-75,6);
    button(-75,58);
    button(75,6);
    button(75,58);

    led(0,19);
    led(0,46);
    led(61,19);
    led(61,46);
    led(-61,19);
    led(-61,46);
    led(12.5,77);
    led(-12.5,77);
    led(-(12.5+25),77);
    led((12.5+25),77);

    rotary(75/2,91);
    rotary(-75/2,91);

    jack(0,21.9);
    jack(0,42.1);
    jack(length,21.9);
    jack(length,42.1);
    jack(length,83);

    midi_jack(11);
    midi_jack(-11);

    power_jack(70);
}

// lid
translate([width + 20, 0, 0]){
    difference() {
        union(){
            roundedBox(width, length, thickness, cornerRadius);
            place_lugs(width, length, lugRadius) cylinder(r=lugRadius, h=thickness);
            difference() {
                translate([thickness+lidTolerance,thickness+lidTolerance]) {
                    roundedBox(width-2*(thickness+lidTolerance),length-2*(thickness+lidTolerance),2*thickness,cornerRadius);
                }
                place_lugs(width, length, lugRadius) cylinder(r=lugRadius+lidTolerance, h=3*thickness);
           }
        }
        difference() {
            translate([2*thickness,2*thickness, 1*thickness]){
                roundedBox(width-4*thickness,length-4*thickness, 3*thickness, cornerRadius);
            }
            place_lugs(width, length, lugRadius) cylinder(r=lugRadius+thickness, h=2*thickness);
        }
        // screw hole
        translate([0,0,-height/2]){
            screwHole = 3.2; // M3 close fit clearance hole size
            place_lugs(width, length, lugRadius) cylinder(d=screwHole, h=height);
        }

        // counterbore
        translate([0,0,-2.5]){
            place_lugs(width, length, lugRadius) cylinder(h=4, r1=4, r2=0);
        }
    }
}

module button(x,y){
    translate([pcbBottom+y, length/2+x,-height/2]){
        difference() {
            cylinder(d=12.2, h=height);
            translate([-7.1,-0.9,0]) {
                 cube([2,1.8,height]);
            }
        }
    }
}

module led(x,y){
    translate([pcbBottom+y, length/2+x,-height/2]){
        cylinder(d=5.1, h=height);
    }
}

module rotary(x,y){
    translate([pcbBottom+y, length/2+x,-height/2]){
        cylinder(d=7.4, h=height);
    }
}

module jack(x,y){
    translate([pcbBottom+y, height/2+x ,pcbHeight-8]){
        rotate(a=90, v=[1,0,0]) {
            cylinder(d=11.2, h=height);
        }
    }
}

module midi_jack(x){
    translate([width-height/2, x+length/2,pcbHeight-2.5]){
        rotate(a=90, v=[0,1,0]) {
            cylinder(d=3.8, h=height);
        }
    }
}

module power_jack(x){
    translate([width-height/2, x-0.3+length/2,pcbHeight+0.5]){
        rotate(a=90, v=[0,1,0]) {
            cube([11.1,9.4,height]);
        }
    }
}

module roundedBox(width, length, height, radius) {
    dRadius = 2*radius;

    translate([radius,radius]){
        minkowski() {
            cube(size=[width-dRadius,length-dRadius, height]);
            difference() {
                sphere(r=radius);
                translate([-radius,-radius,0]) {
                  cube([2*radius,2*radius,radius]);
                }
            }
        }
    }
}

//default values are for M3 nut
module nut_trap (
        w = 5.5,
        h = 3.1
        )
{
        cylinder(r = w / 2 / cos(180 / 6) + 0.05, h=h, $fn=6);
}

module place_lugs(length=80, width=40, margin=3) {
    translate([margin,margin]){
        children();
    }
    translate([margin,width-margin]){
        children();
    }
    translate([margin,width/2]){
        children();
    }
    translate([length-margin,width/2]){
        children();
    }
    translate([length-margin,margin]){
        children();
    }
    translate([length-margin,width-margin]){
        children();
    }
}



