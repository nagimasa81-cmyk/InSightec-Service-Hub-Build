
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes("function autoPanelDetect"),"shared auto panel detector missing");
ok(c.includes("const q=plotFromGrid(ctx,canvas,roi)"),"auto detector must use exact plotFromGrid provider");
ok(c.includes("shared-analysis-core-auto-panel"),"shared source tag missing");
ok(a.includes("EGSAnalysisV2.autoPanelDetect(ctx,canvas)"),"app does not call shared detector");
ok(!a.includes("function structureScore("),"legacy independent Auto ROI heuristic still present");
ok(a.includes("if(!v2 && !roiManual)"),"auto analyze recovery missing");
console.log("v3.0.1 shared Auto ROI regression PASS");
