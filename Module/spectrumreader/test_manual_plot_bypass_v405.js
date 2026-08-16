
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(c.includes('function prepareManualROI'),'manual prepare missing');
ok(c.includes("source:'manual-roi-direct-no-localizer'"),'manual direct source missing');
ok(c.includes("source:'manual-roi-relative-geometry'"),'relative geometry missing');
ok(a.includes('if(!v2 && roiManual)'),'manual bypass branch missing');
ok(a.includes('EGSAnalysisV2.prepareManualROI(ctx,canvas,analysisROI)'),'manual bypass call missing');
const manualPos=a.indexOf('if(!v2 && roiManual)');
const fatalPos=a.indexOf('if(!v2){',manualPos);
ok(manualPos>=0&&fatalPos>manualPos,'manual bypass must precede fatal gate');
console.log('v4.0.5 manual plot-localizer bypass regression PASS');
