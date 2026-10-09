// The "negative" of every hole type, side by side (gauge 10, countersunk).
// This is the solid that gets subtracted from your part.
include <../screw_holes.scad>

gauge = 10;
spacing = 16;
screw = SCREW_UNIT_UK_GAUGE + SCREW_HEAD_COUNTERSUNK + SCREW_FOR_METAL;

holes = [HOLE_PILOT, HOLE_SNUG, HOLE_CLEARANCE,
         HOLE_RIBBED, HOLE_RIBBED_TWIST,
         HOLE_TRI, HOLE_TRI_TWIST,
         HOLE_DROP];

// Upside down (head on the floor) so the render shows each cross-section end-on.
for (i = [0:len(holes)-1])
    right(i * spacing)
        xrot(180)
        zrot(holes[i] == HOLE_DROP ? 180 : 0)  // drop's point away from the camera
        self_tap_hole(gauge=gauge, length=20, screw_type=screw,
                      hole_type=holes[i], anchor=TOP, sink=1);
