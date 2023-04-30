// pedalboard case

$fn=200;

length = 180;
width= 100;
height = 30;
cornerRadius = 1;
thickness = 2;
screwHoleRadius = 1.6;
lugRadius = 3.2;
screwRadius = 1.25;
lidTolerance = 0.3;


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
                translate([thickness+lidTolerance,thickness+lidTolerance]) {
                    roundedBox(width-2*(thickness+lidTolerance),length-2*(thickness+lidTolerance),2*thickness,cornerRadius);
                }
                lugs(width, length, 3*thickness, lugRadius, lugRadius+lidTolerance);
           }
        }
        difference() {
            translate([2*thickness,2*thickness, 0.5*thickness]){
                roundedBox(width-4*thickness,length-4*thickness, 3*thickness, cornerRadius);
            }
            lugs(width,length,2*thickness,lugRadius,lugRadius+thickness);
        }
        translate([0,0,-5*thickness]){
            lugs(width, length, 10*thickness, lugRadius, screwHoleRadius);
        }

      // FIXME 
      //  translate([0,0,-10*thickness]){
      //      lugs(width, length, 10*thickness, lugRadius, lugRadius);
      //  }

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


