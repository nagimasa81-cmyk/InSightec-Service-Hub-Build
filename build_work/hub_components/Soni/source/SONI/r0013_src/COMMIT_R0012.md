# RC2-R0012 XD Geometry and Color Fidelity

- Preserves the validated R0010/R0011 replay and channel-calibration paths.
- Adds Adaptive, Manual, and Normalized XD scale modes.
- Adds adjustable gamma with conservative workstation-like default.
- Uses robust 1st/99th percentile scaling in Adaptive mode to avoid isolated-value colour saturation.
- Keeps Element SDR on a fixed 0.00–1.00 scale unless Manual is selected.
- Derives ring guides from actual element radii instead of fixed decorative circles.
- Derives six sector boundaries from the largest angular gaps in the actual element cloud.
- Uses radius-dependent dot sizes: larger in the dense centre, smaller at the outer ring.
- Restricts magenta to the extreme top of the LUT so broad regions no longer collapse to magenta.
