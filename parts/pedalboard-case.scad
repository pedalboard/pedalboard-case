// pedalboard case

$fn=200;

length = 180;
width= 100;
height = 30;
cornerRadius = 2;
thickness = 2;
screwHoleRadius = 1.6;
lugRadius = 3.2;
screwRadius = 1.25;


// box
difference() {
    union() {
        difference() {
            roundedBox(width, length, height, cornerRadius);
            translate([thickness,thickness,thickness]) {
                roundedBox(width-(2*thickness), length-(2*thickness), height, cornerRadius);
            }
        }
        lugs(width, length, height, lugRadius, lugRadius);
    }
    translate([0,0,2*thickness]){
        lugs(width, length, height, lugRadius, screwRadius);
    }
}

// lid
translate([width + 10, 0, 0]){
    difference() {
        union(){
            roundedBox(width, length, thickness, cornerRadius);
            lugs(width, length, thickness, lugRadius, lugRadius);
            difference() {
                translate([thickness,thickness]) {
                    roundedBox(width-2*thickness,length-2*thickness,2*thickness,cornerRadius);
                }
                lugs(width, length, 3*thickness, lugRadius, lugRadius);
           }
        }
        difference() {
            translate([2*thickness,2*thickness, 0.5*thickness]){
                cube([width-4*thickness,length-4*thickness, 3*thickness]);
            }
            lugs(width,length,2*thickness,lugRadius,lugRadius+thickness);
        }
        translate([0,0,-thickness]){
            lugs(width, length, 4*thickness, lugRadius, screwHoleRadius);
        }
    }

}


module roundedBox(width, length, height, radius) {
    dRadius = 2*radius;

    translate([radius,radius]){
        minkowski() {
            cube(size=[width-dRadius,length-dRadius, height]);
            cylinder(r=radius, h=0.0001);
        }
    }
}

module lugs(length, width, height, margin, radius) {
    translate([margin,margin]){
        cylinder(r=radius, h=height);
    }
    translate([margin,width-margin]){
        cylinder(r=radius, h=height);
    }
    translate([margin,width/2]){
        cylinder(r=radius, h=height);
    }
    translate([length-margin,width/2]){
        cylinder(r=radius, h=height);
    }
    translate([length-margin,margin]){
        cylinder(r=radius, h=height);
    }
    translate([length-margin,width-margin]){
        cylinder(r=radius, h=height);
    }
}


