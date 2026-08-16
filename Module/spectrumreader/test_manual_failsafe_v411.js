
const fs=require('fs'),a=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
const m=a.indexOf("if(roiManual){");
const local=a.indexOf("EGSAnalysisV2.prepare(ctx,canvas,analysisROI)",m);
const fallback=a.indexOf("EGSAnalysisV2.prepareManualROI(ctx,canvas,analysisROI)",m);
const stable=a.indexOf("snappedPanel=stableEnergyPanel()",m);
ok(m>=0&&local>m&&fallback>local&&stable>fallback,"manual order must be local -> fallback -> optional stable");
ok(a.includes("stableEnergyPanel non-fatal failure"),"stable panel guard missing");
ok(a.includes("manual stable snap ignored"),"optional stable snap guard missing");
ok(a.includes("els.result.classList.add('hidden')"),"stale result clearing missing");
console.log("v4.1.2 manual fail-safe regression PASS");
