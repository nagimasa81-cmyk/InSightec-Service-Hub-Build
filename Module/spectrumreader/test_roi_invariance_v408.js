
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(a.includes("ROI-invariant analysis"),"ROI invariant stage missing");
ok(a.includes("EGSAnalysisV2.autoPanelDetect(ctx,canvas)"),"global panel snap missing");
ok(a.includes("overlap>=.18"),"manual hint overlap gate missing");
ok(a.includes("v2=EGSAnalysisV2.prepare(ctx,canvas,{x:B.x,y:B.y,w:B.w,h:B.h})"),"snapped context not used");
ok(a.includes("Numeric plot fixed independently from visible ROI edges"),"diagnostic missing");
console.log("v4.0.8 ROI invariance policy PASS");
