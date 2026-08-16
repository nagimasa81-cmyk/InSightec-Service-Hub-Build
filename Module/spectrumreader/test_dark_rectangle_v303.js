
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes("detect a DARK RECTANGLE, not a connected black blob"),"method change missing");
ok(c.includes("function interiorStats"),"interior darkness scoring missing");
ok(c.includes("function edgeDarkRatio"),"four edge scoring missing");
ok(c.includes("verticalDarkness")&&c.includes("horizontalDarkness"),"boundary refinement missing");
ok(c.includes("energy-dark-rectangle-boundary"),"new source tag missing");
ok(!c.includes("Connected dark components in coarse coordinates"),"legacy connected-component detector remains");
console.log("v3.0.3 dark rectangle boundary regression PASS");
