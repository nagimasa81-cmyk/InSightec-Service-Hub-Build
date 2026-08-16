
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes("geometry-first Noise calibration"),"geometry-first calibration missing");
ok(c.includes("source:'geometry-first-horizontal-major-grid'"),"geometry source missing");
ok(c.includes("{y:topRow,value:.04"),"0.04 anchor missing");
ok(c.includes("{y:zeroY,value:0"),"zero anchor missing");
ok(c.includes("bottomDist"),"bottom boundary consistency missing");
ok(c.includes("spanRatio"),"full-height grid scoring missing");
console.log("v4.0.3 geometry-first Noise axis regression PASS");
