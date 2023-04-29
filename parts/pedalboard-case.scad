// pedalboard case

$fn=200;

length = 180;
width= 100;
height = 30;
cornerRadius = 3;
thickness = 2;


// box
translate([cornerRadius, cornerRadius, 0]){
    difference() {
            roundedBox(length, width, height, cornerRadius); 
            translate([thickness,thickness,thickness]) {
                roundedBox(length-(2*thickness), width-(2*thickness), height-thickness, cornerRadius); 
            }
    }
    lugs(width, length, height, cornerRadius);
}

// lid
translate([width*2 + 10 + cornerRadius, cornerRadius , 0]){
    mirror([1,0,0]) {
        roundedBox(length, width, thickness, cornerRadius);
        difference() {
            translate([thickness,thickness,0]) {
                roundedBox(length-2*thickness,width-2*thickness,2*thickness,cornerRadius);
            }
            lugs(width, length, height, cornerRadius);
            translate([2*thickness-cornerRadius,2*thickness-cornerRadius,1*thickness]) {
                difference() {
                    cube([width-4*thickness,length-4*thickness,thickness]);
                    lugs(width+2*thickness, length+2*thickness, thickness, cornerRadius+thickness);
                }
            }
        }
    }
}


module roundedBox(length, width, height, radius)
{
    dRadius = 2*radius;

    //base rounded shape
    minkowski() {
        cube(size=[width-dRadius,length-dRadius, height]);
        cylinder(r=radius, h=0.0001);
    }
}

module lugs(length, width, height, radius)
{
    dRadius = 2*radius;
    translate([0,0]){
        cylinder(r=radius, h=height);
    }
 
    translate([0,width-dRadius]){
        cylinder(r=radius, h=height);
    }
    translate([length-dRadius,0]){
        cylinder(r=radius, h=height);
    }
    translate([length-dRadius,width-dRadius]){
        cylinder(r=radius, h=height);
    }
}


