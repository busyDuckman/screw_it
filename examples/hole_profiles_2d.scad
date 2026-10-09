// Plan-view cross-section of every hole type (gauge 10, UK_GAUGE, FOR_METAL).
// Twisted variants are omitted: their slice at any height is the same shape.
// Regenerate docs/img/hole_profiles.svg with tools/make_profiles_svg.py.
include <../screw_holes.scad>

gauge = 10;
screw = SCREW_UNIT_UK_GAUGE + SCREW_HEAD_COUNTERSUNK + SCREW_FOR_METAL;
p = _resolve_screw_params(gauge, screw);  // [shank, thread, head, head_h, pilot]

holes = [HOLE_PILOT, HOLE_SNUG, HOLE_CLEARANCE, HOLE_RIBBED,
         HOLE_TRI, HOLE_DROP];

for (i = [0:len(holes)-1])
    right(i * 10)
        _hole_shape_2d(holes[i], p[0], p[1], p[4], $fn=96);
