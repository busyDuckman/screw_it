// Minimal example: a bracket with two countersunk #8 screw holes.
include <BOSL2/std.scad>
include <../screw_holes.scad>

screw = SCREW_UNIT_UK_GAUGE + SCREW_HEAD_COUNTERSUNK + SCREW_FOR_SOFT_WOOD;

difference() {
    cuboid([60, 20, 6], anchor=TOP, rounding=2, edges="Z");

    for (x = [-20, 20])
        right(x)
            self_tap_hole(gauge=8, length=25, screw_type=screw,
                          hole_type=HOLE_CLEARANCE, anchor=TOP, sink=0.5);
}
