include <BOSL2/std.scad>

// https://www.hammfg.com/files/parts/pdf/1590DD.pdf

$fn=100;

ff=0.001;
case_height=37;
case_width=120;
case_length=188;
case_wall=2.5;

wall=2;

bushing_length=6;
bushing_d=8;

pcb_width=111;
pcb_length=174;
pcb_height=1.6;

jack_height = 25; // FIXME calculate value
midi_height = 25; // FIXME calculate value 

d = 2 * ang();

difference() {
    prismoid(
        size1=[case_length+wall*2,case_width+wall*2], 
        size2=[case_length+wall*2-d,case_width+wall*2-d], 
        h=case_height+wall);
    down(ff) prismoid(
        size1=[case_length,case_width], 
        size2=[case_length-d,case_width-d], 
        h=case_height);
   bushings() down(10) cylinder(h=20,d=bushing_d);
}


bushings() bushing();

module bushings() {
    fwd(pcb_width/2-(case_width-pcb_width)/2+case_wall) {
        up(case_height+wall+3) {
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
            left((case_length+bushing_length)/2+wall-ang(jack_height)) 
                yrot(90) {
                back(28) children();
                back(48) children();
                back(89) children();
            }
            right((case_length+bushing_length)/2+wall-ang(jack_height)) 
                yrot(90) {
                back(28) children();
                back(48) children();
                back(89) children();
            }
        }
        up(midi_height) { 
            back(111+case_wall+wall+bushing_length/2-ang(midi_height)) 
                xrot(90) {
                left(15) children();
                right(15) children();
            }
        };
        pcb();
    }
}

// the angle of the side walls is 88 deg
function ang(h=case_height) = h / tan(88);

module bushing() {
    tube(h=bushing_length,wall=6,id=bushing_d);
}

module pcb() {
    left(pcb_length/2) color("green") 
        cube([pcb_length, pcb_width, pcb_height]);
}




