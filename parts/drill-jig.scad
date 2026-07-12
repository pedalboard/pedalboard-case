include <BOSL2/std.scad>

// https://www.hammfg.com/files/parts/pdf/1590DD.pdf

$fn=100;

ff=0.01;

// outer hight of 1599DD case
case_height=37;
// max width 1599DD case (bottom)
case_width=120;
// max length 1599DD case (bottom)
case_length=188;
// wall thickness of the case
case_wall=2.5;

// wasll thickness of the jig
wall=2;

// the length of the bushing
bushing_length=6;
// the innder diameter of the bushing
bushing_id=8.1;
// the outer diameter of the bushing
bushing_od=20;

// the width of the PCB
pcb_width=111;
// the length of the PCB
pcb_length=174;
// the thickness of the PCB
pcb_height=1.6;
// should the PCB be rendered
pcb_render=false;

// display cutout (OLED glass pass-through)
// glass: 34.3 x 36.5 mm + 0.1mm clearance per side
display_cutout_w = 34.5;
display_cutout_h = 36.7;
// corner drill diameter for display cutouts
display_corner_drill = 3;

// push button height above PCB
button_height = 5;
// Actuator s-nut + spring
actuator_height = 5 + 6.5; // https://www.cliffuk.co.uk/products/switches/FC7125.pdf

// the height of the PCB's top surface
pcb_top=case_height - case_wall - pcb_height - button_height - actuator_height;

jack_height = pcb_top + 8;
midi_height = pcb_top + 2.5;

// the angle of the side walls is 88 deg
side_angle = 88;

d = 2 * ang();

color([0.3,0.3,0.3,1]) difference() {
    union() {
        prismoid(
           size1=[case_length+wall*2,case_width+wall*2],
            size2=[case_length+wall*2-d,case_width+wall*2-d],
            h=case_height+wall);
        bushings() bushing();
        display_corners() bushing(id=display_corner_drill);
    }
    // remove the case
    down(ff) prismoid(
        size1=[case_length,case_width],
        size2=[case_length-d,case_width-d],
        h=case_height);
    // drill holes
    bushings() down(bushing_length/2+1) cylinder(h=wall+10,d=bushing_id);
    // display corner drill holes
    display_corners() down(bushing_length/2+1) cylinder(h=wall+10,d=display_corner_drill);
}

if (pcb_render) pcb();

module bushings() {
    fwd(pcb_width/2-(case_width-pcb_width)/2+case_wall) {
        up(case_height+bushing_length/2) {
            back(12) {
                children();
                right(75) children();
                left(75) children();
            };
            back(64) {
                children();
                right(75) children();
                left(75) children();
            };
            back(83) {
                right(12.5) children();
                left(12.5) children();
            };
            back(97) {
                right(12.5+25) children();
                left(12.5+25) children();
            };
        };
        up(jack_height) {
            left((case_length+bushing_length)/2-bushing_ang(jack_height))
                yrot(-90) {
                back(28) children();
                back(48) children();
                back(89) children();
            }
            right((case_length+bushing_length)/2-bushing_ang(jack_height))
                yrot(90) {
                back(28) children();
                back(48) children();
                back(89) children();
            }
        }
        back(111+case_wall+bushing_length/2-bushing_ang(midi_height)) {
            up(midi_height) {
                xrot(-90) {
                    left(15) children();
                    right(15) children();
                }
            }
            up(pcb_top + (case_height - case_wall - pcb_top)/2 ) right(55) xrot(-90) children();
        }
    }
}

// bushing correction for wall angle
function bushing_ang(h) = ang(h+bushing_od/2);

// correction for wall angle
function ang(h=case_height) = h / tan(side_angle);

module bushing(id=bushing_id) {
    tube(h=bushing_length,od=bushing_od,id=id);
}

// display cutout corner positions (4 corners × 2 displays)
// displays centered at back(34.8), left/right(37.5) from PCB reference
module display_corners() {
    fwd(pcb_width/2-(case_width-pcb_width)/2+case_wall) {
        up(case_height+bushing_length/2) {
            // Display 1 (left) - center at back(34.8) left(37.5)
            back(34.8 - display_cutout_h/2) left(37.5 + display_cutout_w/2) children();
            back(34.8 - display_cutout_h/2) left(37.5 - display_cutout_w/2) children();
            back(34.8 + display_cutout_h/2) left(37.5 + display_cutout_w/2) children();
            back(34.8 + display_cutout_h/2) left(37.5 - display_cutout_w/2) children();
            // Display 2 (right) - center at back(34.8) right(37.5)
            back(34.8 - display_cutout_h/2) right(37.5 - display_cutout_w/2) children();
            back(34.8 - display_cutout_h/2) right(37.5 + display_cutout_w/2) children();
            back(34.8 + display_cutout_h/2) right(37.5 - display_cutout_w/2) children();
            back(34.8 + display_cutout_h/2) right(37.5 + display_cutout_w/2) children();
        }
    }
}

module pcb() {
    fwd(ang(pcb_top)-4.5+case_wall)
        up(pcb_top-pcb_height)
        color("green")
        cube([pcb_length, pcb_width, pcb_height], center=true);
}




