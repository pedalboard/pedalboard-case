include <BOSL2/std.scad>
include <BOSL2/screws.scad>

$fn=200;

oled_display();

module oled_display() {

    difference() {
        union() {
          color("blue")
          up(0.6) cuboid(size=[34.3,45.5,1.2]);
          color("gray")
          up(2) cuboid(size=[34.3,36.5,1.6]);
          color("black")
          fwd(3) up(2.8) cuboid(size=[28.86,28.86,0.05]);
          color("white")
          fwd(3) up(2.81) cuboid(size=[26.86,26.86,0.05]);
        }
        back(20.75) left(15.15) up(2) screw_hole("M2",length=10, oversize=[0,0],anchor=TOP);
        back(20.75) left(-15.15) up(2) screw_hole("M2",length=10, oversize=[0,0],anchor=TOP);
        back(-20.75) left(15.15) up(2) screw_hole("M2",length=10, oversize=[0,0],anchor=TOP);
        back(-20.75) left(-15.15) up(2) screw_hole("M2",length=10, oversize=[0,0],anchor=TOP);
        back(20.35) cuboid(size=[10.3,4.9,6]);
    }
}


