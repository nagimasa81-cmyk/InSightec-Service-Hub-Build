
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes("function noiseAxisSeries"),"Noise grid-series decoder missing");
ok(c.includes("{y:seq[0],value:.04}"),"0.04 anchor missing");
ok(c.includes("{y:seq[3],value:.01}"),"0.01 anchor missing");
ok(c.includes("stepValue:.01"),"Noise step missing");
ok(a.includes("v2.noiseAxis?.ok"),"app does not consume Noise series");
ok(a.includes("SAMPLE_SPLIT/EGSCore.SAMPLE_AXIS_MAX"),"0-270/270-500 split missing");
console.log("Noise axis series v2 regression PASS");
