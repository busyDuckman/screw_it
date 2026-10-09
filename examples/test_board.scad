// Printable calibration board: every hole type x gauges 4, 6, 8, 10.
// Print it, then try your screws in each hole to pick what works for you.
include <../screw_holes.scad>

narrow = false;  // true -> use the UK_GAUGE_NARROW sizing

if (narrow)
    test_board(SCREW_UNIT_UK_GAUGE_NARROW, "UK Gauge (Narrow)");
else
    test_board(SCREW_UNIT_UK_GAUGE, "UK Gauge");
