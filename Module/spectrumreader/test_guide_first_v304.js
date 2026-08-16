
const fs=require('fs');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
const a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(c.includes("function guideAlignedPanelDetect"),"guide-first detector missing");
ok(c.includes("function localPanelBoundaryFromPlot"),"local panel boundary missing");
ok(c.includes("guide-first-grid-then-local-panel"),"guide-first source tag missing");
ok(c.includes("const q=plotFromGrid(ctx,canvas,roi)"),"regular grid provider missing");
ok(a.includes("sourceGuideCropped")&&a.includes("guideAlignedPanelDetect"),"camera path not routed to guide-first detector");
ok(a.includes(": EGSAnalysisV2.autoPanelDetect"),"file-image fallback missing");
ok(a.includes("撮影枠内だけでEnergy per Bandの緑gridを探し"),"guide-first camera status missing");
console.log("v3.0.4 guide-first regression PASS");
