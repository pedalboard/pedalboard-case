// pedalboard case

$fn=200;

length = 180;
width= 115;
height = 30;
cornerRadius = 1;
thickness = 2;
lugRadius = 3.2;
lidTolerance = 0.3;
pcbBottom = 6;

pcbHeight = thickness+15.8; // given by the button


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
        screwRadius = 1.25; // M3 tapping drill size
        lugs(width, length, height, lugRadius, screwRadius);
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
            screwHoleRadius = 1.6; // M3 close fit clearance hole size
            lugs(width, length, 10*thickness, lugRadius, screwHoleRadius);
        }

      // FIXME add counterbore
      //  translate([0,0,-10*thickness]){
      //      lugs(width, length, 10*thickness, lugRadius, lugRadius);
      //  }

    }

}

module button(x,y){
    translate([pcbBottom+y, length/2+x,-height/2]){
        difference() {
            cylinder(r=6.1, h=height);
            translate([-7.1,-0.9,0]) {
                 cube([2,1.8,height]);
            }
        }
    }
}

module led(x,y){
    translate([pcbBottom+y, length/2+x,-height/2]){
        cylinder(r=2.56, h=height);
    }
}

module rotary(x,y){
    translate([pcbBottom+y, length/2+x,-height/2]){
        cylinder(r=3.7, h=height);
    }
}

module jack(x,y){
    translate([pcbBottom+y, height/2+x ,pcbHeight-8]){
        rotate(a=90, v=[1,0,0]) {
            cylinder(r=5.6, h=height);
        }
    }
}

module midi_jack(x){
    translate([width-height/2, x+length/2,pcbHeight-2.5]){
        rotate(a=90, v=[0,1,0]) {
            cylinder(r=1.9, h=height);
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

module lugs(length, width, height, margin, radius) {
    translate([margin,margin]){
        cylinder(r=radius, h=height);
    }
    translate([margin,width-margin]){
        cylinder(r=radius, h=height);
    }
    /*
    translate([margin,width/2]){
        cylinder(r=radius, h=height);
    }
    translate([length-margin,width/2]){
        cylinder(r=radius, h=height);
    }
    */
    translate([length-margin,margin]){
        cylinder(r=radius, h=height);
    }
    translate([length-margin,width-margin]){
        cylinder(r=radius, h=height);
    }
}



