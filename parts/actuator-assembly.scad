include <lib/actuator.scad>

$fn=100;

pcb_thickness = 1.6;

actuator();
up(5+4.5+pcb_thickness) actuator_nut();
up(5+2.5+pcb_thickness) led_ring_washer();
