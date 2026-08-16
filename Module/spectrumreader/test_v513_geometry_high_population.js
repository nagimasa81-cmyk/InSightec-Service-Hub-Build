
const fs=require('fs');
const a=fs.readFileSync('analysis_core_v2.js','utf8');
const c=fs.readFileSync('core.js','utf8');
const app=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw Error(m)}

ok(a.includes("left:(P.x-R.x)/Math.max(1,R.w)"),'known plot left inset not normalized');
ok(a.includes("top:(P.y-R.y)/Math.max(1,R.h)"),'known plot top inset not normalized');
ok(c.includes("Math.abs(v)>1.25?v/Math.max(1,dim):v"),'legacy pixel inset guard missing');
ok(c.includes("if(left+right>.94)"),'degenerate horizontal geometry guard missing');
ok(a.includes("source:'regional-signal-population-v5.1.4'"),'regional signal population missing');
ok(a.includes("rise>=.28 && supportOK && enoughPixels"),'High elevated population criterion missing');
ok(a.includes("highSelection:highModel.riseFromLowSteps>=.28?'distinct-elevated-population':'dominant-population'"),
   'High selection diagnostic missing');

const m0=app.indexOf("analysisStage='manual-authoritative-scoped'");
const m1=app.indexOf("EGSAnalysisV2.prepareManualROI(ctx,canvas,analysisROI)",m0);
const m2=app.indexOf("EGSAnalysisV2.prepare(ctx,canvas,analysisROI)",m0);
ok(m0>=0&&m1>m0&&m2>m1,'Manual must run scoped prepareManualROI before generic prepare');

console.log('v5.1.4 geometry/high-population regression PASS');
