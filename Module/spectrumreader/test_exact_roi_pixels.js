
const fs=require('fs');
const s=fs.readFileSync('app.js','utf8');
function ok(v,m){if(!v)throw new Error(m)}
ok(s.includes("function exactAnalysisROI"),"exactAnalysisROI missing");
ok(s.includes("const analysisROI=exactAnalysisROI(roi)"),"visible ROI not frozen to exact pixels");
ok(s.includes("roi={...analysisROI};"),"red ROI not synchronized to exact pixels");
ok(s.includes("checkedChannels(analysisROI)"),"channel checkbox stage must use exact user ROI");
ok(s.includes("EGSAnalysisV2.prepare(ctx,canvas,analysisROI)"),"v2 plot search must start from exact ROI");
ok(s.includes("const analysisBox=v2.context"),"v2 plot context missing");
ok(s.includes("calibrateTrack(scaled,analysisBox"),"numeric calibration must use plot context");
console.log("Exact ROI -> v2 plot-context contract PASS");
