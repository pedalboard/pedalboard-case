include <lib/actuator.scad>

$fn=200;

pcb_thickness = 1.6;

actuator();
up(5+3+pcb_thickness) actuator_nut();
up(5+1.5+pcb_thickness) led_ring_washer();
