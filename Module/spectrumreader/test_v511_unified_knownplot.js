
const fs=require('fs');
const a=fs.readFileSync('app.js','utf8');
const c=fs.readFileSync('analysis_core_v2.js','utf8');
function ok(v,m){if(!v)throw Error(m)}
ok(c.includes('function prepareKnownPanel('),'prepareKnownPanel missing');
ok(c.includes("version:'known-plot-v5.1.4'"),'known plot version missing');
ok(a.includes("Camera and Library both analyze the same immutable ImageData first"),'unified camera/library path missing');
ok(a.includes("activeDetectedPanel={...found,plot:found.plot?{...found.plot}:null}"),'auto plot cache missing');
ok(a.includes("EGSAnalysisV2.prepareKnownPanel(ctx,canvas,analysisROI,activeDetectedPanel.plot"),'Analyze does not reuse known plot');
ok(a.indexOf("found=detectGraph()") < a.indexOf("const reg=applyCanonicalRegistration()", a.indexOf("function runPostCapturePipeline")),
   'camera pipeline must try direct detector before registration');
ok(a.includes("cropMeta.numeric_plot"),'actual numeric plot diagnostic missing');
console.log('v5.1.1 unified input / known plot regression PASS');
