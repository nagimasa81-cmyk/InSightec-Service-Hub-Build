
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes("function plotFromGrid"),"plot locator missing");
ok(c.includes("function axisStripFamily"),"Y-axis strip decoder missing");
ok(c.includes("long decimal Y-axis glyphs"),"Noise decimal visual rule missing");
ok(c.includes("short Gain Y-axis glyphs"),"Gain visual rule missing");
ok(a.includes("axisFamilyAuthoritative:true"),"Auto axis family not authoritative");
ok(a.includes("chooseForegroundTrace(analysisBox"),"trace not using v2 plot context");
ok(a.includes("gainPixelLevelSummary(tr,analysisBox"),"Gain numeric stage not using v2 context");
console.log("Analysis Core v2 architecture regression PASS");
