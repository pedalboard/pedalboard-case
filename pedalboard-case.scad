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
}

// lid
translate([width*2 + 10 + cornerRadius, cornerRadius , 0]){
    mirror([1,0,0]) {
        roundedBox(length, width, thickness, cornerRadius);
        difference() {
            translate([thickness,thickness,0]) {
                roundedBox(length-2*thickness,width-2*thickness,2*thickness,cornerRadius);
            }
            translate([2*thickness,2*thickness,0]) {
                roundedBox(length-4*thickness,width-4*thickness,4*thickness,cornerRadius);
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


